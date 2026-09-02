import os
import argparse
import logging
import pandas as pd
from google.cloud import bigquery
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Key USDA nutrient IDs
NUTRIENT_MAP = {
    1008: "calories",
    1003: "protein_g",
    1004: "fat_g",
    1005: "carbs_g",
    1079: "fiber_g",
    2000: "sugar_g",
    1093: "sodium_mg"
}

def run_usda_etl(data_dir: str, dry_run: bool = False):
    """
    Ingests and merges USDA Foundation Foods and SR Legacy datasets into BigQuery usda_foods table.
    """
    food_csv = os.path.join(data_dir, "food.csv")
    food_nutrient_csv = os.path.join(data_dir, "food_nutrient.csv")
    
    logger.info(f"Loading foods catalog from {food_csv}...")
    df_food = pd.read_csv(food_csv, usecols=["fdc_id", "data_type", "description"])
    
    # Filter only to Foundation and SR Legacy foods
    target_types = ["foundation_food", "sr_legacy_food", "sample_food"]
    df_food_filtered = df_food[df_food["data_type"].isin(target_types)].copy()
    logger.info(f"Filtered {len(df_food_filtered)} Foundation and SR Legacy food items.")
    
    valid_fdc_ids = set(df_food_filtered["fdc_id"])

    logger.info(f"Processing nutrients from {food_nutrient_csv} in chunks...")
    target_nutrient_ids = set(NUTRIENT_MAP.keys())
    
    nutrient_rows = []
    # Stream in chunks for memory efficiency
    for chunk in pd.read_csv(food_nutrient_csv, usecols=["fdc_id", "nutrient_id", "amount"], chunksize=200000):
        matched = chunk[(chunk["fdc_id"].isin(valid_fdc_ids)) & (chunk["nutrient_id"].isin(target_nutrient_ids))]
        if not matched.empty:
            nutrient_rows.append(matched)
            
    df_nutrients = pd.concat(nutrient_rows, ignore_index=True)
    df_nutrients["nutrient_name"] = df_nutrients["nutrient_id"].map(NUTRIENT_MAP)
    
    logger.info(f"Pivoting {len(df_nutrients)} nutrient records...")
    df_pivot = df_nutrients.pivot_table(
        index="fdc_id",
        columns="nutrient_name",
        values="amount",
        aggfunc="first"
    ).reset_index()
    
    # Merge food description with nutrients
    df_merged = pd.merge(df_food_filtered, df_pivot, on="fdc_id", how="left")
    
    # Fill missing values
    for col in ["calories", "protein_g", "fat_g", "carbs_g", "fiber_g", "sugar_g", "sodium_mg"]:
        if col not in df_merged.columns:
            df_merged[col] = 0.0
        else:
            df_merged[col] = df_merged[col].fillna(0.0).round(2)
            
    df_merged["fdc_id"] = df_merged["fdc_id"].astype(str)
    
    logger.info(f"Cleaned dataset: {len(df_merged)} whole food items ready for BigQuery.")

    if dry_run:
        logger.info(f"Dry run complete. Sample data:\n{df_merged.head(3)}")
        return

    # Ingest into BigQuery
    client = bigquery.Client(project=settings.PROJECT_ID)
    dataset_ref = bigquery.DatasetReference(settings.PROJECT_ID, settings.BIGQUERY_DATASET)
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        client.create_dataset(dataset)
        logger.info(f"Created BigQuery dataset: {settings.BIGQUERY_DATASET}")

    table_id = f"{settings.PROJECT_ID}.{settings.BIGQUERY_DATASET}.usda_foods"
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    
    client.load_table_from_dataframe(df_merged, table_id, job_config=job_config).result()
    logger.info(f"Successfully loaded {len(df_merged)} rows into BigQuery table: {table_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NextBite USDA FoodData Central ETL pipeline")
    parser.add_argument("--data-dir", default="c:/Users/Administrator/Documents/nextbite/data/usda", help="Path to USDA data directory")
    parser.add_argument("--dry-run", action="store_true", help="Perform parsing without BigQuery write")
    args = parser.parse_args()
    run_usda_etl(args.data_dir, args.dry_run)

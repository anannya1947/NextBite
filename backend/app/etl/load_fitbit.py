import os
import argparse
import logging
import pandas as pd
from google.cloud import bigquery
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def run_fitbit_etl(data_dir: str, dry_run: bool = False):
    """
    Ingests Fitbit dataset CSVs, performs aggregations and loads to BigQuery.
    """
    activity_csv = os.path.join(data_dir, "dailyActivity_merged.csv")
    sleep_csv = os.path.join(data_dir, "sleepDay_merged.csv")
    heartrate_csv = os.path.join(data_dir, "heartrate_seconds_merged.csv")

    logger.info(f"Loading activity data from {activity_csv}...")
    df_activity = pd.read_csv(activity_csv)
    df_activity["ActivityDate"] = pd.to_datetime(df_activity["ActivityDate"]).dt.strftime("%Y-%m-%d")
    df_activity.rename(columns={
        "Id": "user_id",
        "ActivityDate": "activity_date",
        "TotalSteps": "total_steps",
        "TotalDistance": "total_distance",
        "Calories": "calories_burned",
        "VeryActiveMinutes": "very_active_minutes",
        "FairlyActiveMinutes": "fairly_active_minutes",
        "LightlyActiveMinutes": "lightly_active_minutes",
        "SedentaryMinutes": "sedentary_minutes"
    }, inplace=True)
    df_activity["user_id"] = df_activity["user_id"].astype(str)

    logger.info(f"Loading sleep data from {sleep_csv}...")
    df_sleep = pd.read_csv(sleep_csv)
    df_sleep["SleepDay"] = pd.to_datetime(df_sleep["SleepDay"]).dt.strftime("%Y-%m-%d")
    df_sleep.rename(columns={
        "Id": "user_id",
        "SleepDay": "activity_date",
        "TotalMinutesAsleep": "total_minutes_asleep",
        "TotalTimeInBed": "total_time_in_bed"
    }, inplace=True)
    df_sleep["user_id"] = df_sleep["user_id"].astype(str)
    # Deduplicate sleep records per day
    df_sleep = df_sleep.groupby(["user_id", "activity_date"], as_index=False).agg({
        "total_minutes_asleep": "sum",
        "total_time_in_bed": "sum"
    })

    df_hr_daily = pd.DataFrame(columns=["user_id", "activity_date", "avg_heart_rate", "resting_heart_rate"])
    if os.path.exists(heartrate_csv):
        logger.info(f"Processing heartrate data from {heartrate_csv}...")
        # Read in chunks to optimize memory
        hr_chunks = []
        for chunk in pd.read_csv(heartrate_csv, chunksize=100000):
            chunk["Time"] = pd.to_datetime(chunk["Time"]).dt.strftime("%Y-%m-%d")
            grouped = chunk.groupby(["Id", "Time"])["Value"].agg(["mean", "min"]).reset_index()
            hr_chunks.append(grouped)
        if hr_chunks:
            all_hr = pd.concat(hr_chunks, ignore_index=True)
            daily_hr = all_hr.groupby(["Id", "Time"]).agg({
                "mean": "mean",
                "min": "min"
            }).reset_index()
            daily_hr.rename(columns={
                "Id": "user_id",
                "Time": "activity_date",
                "mean": "avg_heart_rate",
                "min": "resting_heart_rate"
            }, inplace=True)
            daily_hr["user_id"] = daily_hr["user_id"].astype(str)
            daily_hr["avg_heart_rate"] = daily_hr["avg_heart_rate"].round().astype(int)
            daily_hr["resting_heart_rate"] = daily_hr["resting_heart_rate"].astype(int)
            df_hr_daily = daily_hr

    logger.info(f"Processed: {len(df_activity)} activity records, {len(df_sleep)} sleep records, {len(df_hr_daily)} HR records.")

    if dry_run:
        logger.info("Dry run complete. No data pushed to BigQuery.")
        return

    # Ingest to BigQuery
    client = bigquery.Client(project=settings.PROJECT_ID)
    dataset_ref = bigquery.DatasetReference(settings.PROJECT_ID, settings.BIGQUERY_DATASET)
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        client.create_dataset(dataset)
        logger.info(f"Created BigQuery dataset: {settings.BIGQUERY_DATASET}")

    # Write tables
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    
    activity_table = f"{settings.PROJECT_ID}.{settings.BIGQUERY_DATASET}.fitness_activity"
    client.load_table_from_dataframe(df_activity, activity_table, job_config=job_config).result()
    logger.info(f"Loaded {len(df_activity)} rows into {activity_table}")

    sleep_table = f"{settings.PROJECT_ID}.{settings.BIGQUERY_DATASET}.fitness_sleep"
    client.load_table_from_dataframe(df_sleep, sleep_table, job_config=job_config).result()
    logger.info(f"Loaded {len(df_sleep)} rows into {sleep_table}")

    if not df_hr_daily.empty:
        hr_table = f"{settings.PROJECT_ID}.{settings.BIGQUERY_DATASET}.fitness_heartrate"
        client.load_table_from_dataframe(df_hr_daily, hr_table, job_config=job_config).result()
        logger.info(f"Loaded {len(df_hr_daily)} rows into {hr_table}")

    # Create unified daily_metrics view
    view_id = f"{settings.PROJECT_ID}.{settings.BIGQUERY_DATASET}.daily_metrics"
    view_sql = f"""
    SELECT 
        a.user_id,
        a.activity_date,
        a.total_steps,
        a.total_distance,
        a.calories_burned,
        a.very_active_minutes,
        a.fairly_active_minutes,
        a.lightly_active_minutes,
        a.sedentary_minutes,
        s.total_minutes_asleep,
        s.total_time_in_bed,
        h.avg_heart_rate,
        h.resting_heart_rate
    FROM `{activity_table}` a
    LEFT JOIN `{sleep_table}` s 
        ON a.user_id = s.user_id AND a.activity_date = s.activity_date
    LEFT JOIN `{settings.PROJECT_ID}.{settings.BIGQUERY_DATASET}.fitness_heartrate` h 
        ON a.user_id = h.user_id AND a.activity_date = h.activity_date
    """
    view = bigquery.Table(view_id)
    view.view_query = view_sql
    try:
        client.delete_table(view_id, not_found_ok=True)
        client.create_table(view)
        logger.info(f"Created BigQuery view: {view_id}")
    except Exception as e:
        logger.error(f"Failed to create BigQuery view: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NextBite Fitbit ETL pipeline")
    parser.add_argument("--data-dir", default="c:/Users/Administrator/Documents/nextbite/data/fitbit", help="Path to fitbit data directory")
    parser.add_argument("--dry-run", action="store_true", help="Perform parsing without BigQuery write")
    args = parser.parse_args()
    run_fitbit_etl(args.data_dir, args.dry_run)

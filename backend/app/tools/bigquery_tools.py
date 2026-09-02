from typing import List, Dict, Any, Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)

def get_bigquery_client():
    """Attempts to create a BigQuery client. Returns None if unavailable."""
    try:
        from google.cloud import bigquery
        return bigquery.Client(project=settings.PROJECT_ID)
    except Exception as e:
        logger.debug(f"BigQuery unavailable (using fallback data): {e}")
        return None

def search_usda_foods(query_term: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Searches BigQuery `nextbite.nutrition.usda_foods` table for matching foods.
    Uses parameterized query to prevent SQL injection.
    Returns empty list if BigQuery is unavailable (fallback handled by caller).
    """
    client = get_bigquery_client()
    if not client:
        return []

    try:
        from google.cloud import bigquery
        table_id = f"{settings.PROJECT_ID}.{settings.BIGQUERY_DATASET}.usda_foods"

        sql = f"""
        SELECT fdc_id, description, calories, protein_g, fat_g, carbs_g, fiber_g, sugar_g, sodium_mg
        FROM `{table_id}`
        WHERE LOWER(description) LIKE CONCAT('%', LOWER(@term), '%')
        ORDER BY LENGTH(description) ASC
        LIMIT @limit
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("term", "STRING", query_term.strip()),
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]
        )

        query_job = client.query(sql, job_config=job_config)
        results = []
        for row in query_job:
            results.append({
                "fdc_id": row["fdc_id"],
                "description": row["description"],
                "calories": float(row["calories"]) if row["calories"] is not None else 0.0,
                "protein_g": float(row["protein_g"]) if row["protein_g"] is not None else 0.0,
                "fat_g": float(row["fat_g"]) if row["fat_g"] is not None else 0.0,
                "carbs_g": float(row["carbs_g"]) if row["carbs_g"] is not None else 0.0,
                "fiber_g": float(row["fiber_g"]) if row["fiber_g"] is not None else 0.0,
                "sugar_g": float(row["sugar_g"]) if row["sugar_g"] is not None else 0.0,
                "sodium_mg": float(row["sodium_mg"]) if row["sodium_mg"] is not None else 0.0,
            })
        return results
    except Exception as e:
        logger.warning(f"BigQuery search_usda_foods error (falling back to standard facts): {e}")
        return []

def query_fitness_metrics(user_id: str, limit_days: int = 30) -> List[Dict[str, Any]]:
    """
    Queries unified daily fitness metrics from BigQuery.
    Returns empty list if BigQuery is unavailable (fallback handled by caller).
    """
    client = get_bigquery_client()
    if not client:
        return []

    try:
        from google.cloud import bigquery
        table_id = f"{settings.PROJECT_ID}.{settings.BIGQUERY_DATASET}.daily_metrics"

        sql = f"""
        SELECT 
            CAST(activity_date AS STRING) as activity_date,
            total_steps,
            total_distance,
            calories_burned,
            very_active_minutes,
            fairly_active_minutes,
            lightly_active_minutes,
            sedentary_minutes,
            total_minutes_asleep,
            total_time_in_bed,
            avg_heart_rate,
            resting_heart_rate
        FROM `{table_id}`
        WHERE user_id = @user_id
        ORDER BY activity_date DESC
        LIMIT @limit
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                bigquery.ScalarQueryParameter("limit", "INT64", limit_days),
            ]
        )

        query_job = client.query(sql, job_config=job_config)
        rows = [dict(row) for row in query_job]
        return rows
    except Exception as e:
        logger.warning(f"BigQuery query_fitness_metrics error: {e}")
        return []

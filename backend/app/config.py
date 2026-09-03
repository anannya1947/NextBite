import os
from typing import List
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PROJECT_ID: str = "nextbite-demo"
    FIREBASE_PROJECT_ID: str = "nextbite-demo-737c0"
    BIGQUERY_DATASET: str = "nextbite"
    FIRESTORE_DATABASE: str = "(default)"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-latest"
    PORT: int = 8080
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "https://nextbite-demo-737c0.web.app",
        "https://nextbite-demo-737c0.firebaseapp.com",
        "https://nextbite-frontend-1059896982978.us-central1.run.app"
    ]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

def get_secret(secret_name: str, project_id: str) -> str:
    """Safely retrieves a secret from Google Cloud Secret Manager."""
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        logger.warning(f"Could not retrieve secret '{secret_name}' from Secret Manager: {e}")
        return ""

settings = Settings()

# If GEMINI_API_KEY is not in environment or .env, securely fetch it from Secret Manager
if not settings.GEMINI_API_KEY:
    fetched_key = get_secret("GEMINI_API_KEY", settings.PROJECT_ID)
    if fetched_key:
        settings.GEMINI_API_KEY = fetched_key
        os.environ["GEMINI_API_KEY"] = fetched_key

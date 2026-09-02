from typing import Optional, Dict, Any
import logging
from app.config import settings
from app.models.user import UserProfile, HealthProfile
from app.models.meal_plan import FullMealPlan
from app.models.food_qa import FoodQAResponse

logger = logging.getLogger(__name__)

# In-memory fallback store for local development without Firestore
_local_store: Dict[str, Any] = {}

def _get_store_key(*parts: str) -> str:
    return "/".join(parts)

def get_firestore_client():
    """Attempts to create a Firestore client. Returns None if unavailable."""
    try:
        from google.cloud import firestore
        return firestore.Client(project=settings.PROJECT_ID, database=settings.FIRESTORE_DATABASE)
    except Exception as e:
        logger.debug(f"Firestore unavailable (using in-memory store): {e}")
        return None

def get_user_profile(uid: str) -> Optional[UserProfile]:
    """Retrieves user profile from Firestore."""
    try:
        db = get_firestore_client()
        if db:
            doc_ref = db.collection("users").document(uid)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                return UserProfile(**data)
            return None
    except Exception as e:
        logger.error(f"Firestore get_user_profile error for {uid}: {e}")

    # In-memory fallback
    key = _get_store_key("users", uid)
    data = _local_store.get(key)
    if data:
        return UserProfile(**data) if isinstance(data, dict) else data
    return None

def save_user_profile(profile: UserProfile) -> bool:
    """Saves or updates user profile in Firestore."""
    try:
        db = get_firestore_client()
        if db:
            doc_ref = db.collection("users").document(profile.uid)
            doc_ref.set(profile.model_dump(mode="json"), merge=True)
            return True
    except Exception as e:
        logger.error(f"Firestore save_user_profile error: {e}")

    # In-memory fallback
    key = _get_store_key("users", profile.uid)
    _local_store[key] = profile.model_dump(mode="json")
    logger.info(f"Saved user profile to in-memory store: {profile.uid}")
    return True

def get_health_profile(uid: str) -> Optional[HealthProfile]:
    """Retrieves the latest calculated health profile for a user."""
    try:
        db = get_firestore_client()
        if db:
            doc_ref = db.collection("users").document(uid).collection("health_profile").document("latest")
            doc = doc_ref.get()
            if doc.exists:
                return HealthProfile(**doc.to_dict())
            return None
    except Exception as e:
        logger.error(f"Firestore get_health_profile error for {uid}: {e}")

    # In-memory fallback
    key = _get_store_key("users", uid, "health_profile", "latest")
    data = _local_store.get(key)
    if data:
        return HealthProfile(**data) if isinstance(data, dict) else data
    return None

def save_health_profile(profile: HealthProfile) -> bool:
    """Saves latest health profile in Firestore."""
    try:
        db = get_firestore_client()
        if db:
            doc_ref = db.collection("users").document(profile.uid).collection("health_profile").document("latest")
            doc_ref.set(profile.model_dump(mode="json"))
            return True
    except Exception as e:
        logger.error(f"Firestore save_health_profile error: {e}")

    # In-memory fallback
    key = _get_store_key("users", profile.uid, "health_profile", "latest")
    _local_store[key] = profile.model_dump(mode="json")
    logger.info(f"Saved health profile to in-memory store: {profile.uid}")
    return True

def get_active_meal_plan(uid: str) -> Optional[FullMealPlan]:
    """Retrieves the current active meal plan for a user."""
    try:
        db = get_firestore_client()
        if db:
            doc_ref = db.collection("users").document(uid).collection("meal_plans").document("active")
            doc = doc_ref.get()
            if doc.exists:
                return FullMealPlan(**doc.to_dict())
            return None
    except Exception as e:
        logger.error(f"Firestore get_active_meal_plan error for {uid}: {e}")

    # In-memory fallback
    key = _get_store_key("users", uid, "meal_plans", "active")
    data = _local_store.get(key)
    if data:
        return FullMealPlan(**data) if isinstance(data, dict) else data
    return None

def save_meal_plan(plan: FullMealPlan) -> bool:
    """Saves meal plan to active document and archived history."""
    try:
        db = get_firestore_client()
        if db:
            user_ref = db.collection("users").document(plan.uid)
            # Save as active
            active_ref = user_ref.collection("meal_plans").document("active")
            active_ref.set(plan.model_dump(mode="json"))
            # Also archive with plan_id
            history_ref = user_ref.collection("meal_plans").document(plan.plan_id)
            history_ref.set(plan.model_dump(mode="json"))
            return True
    except Exception as e:
        logger.error(f"Firestore save_meal_plan error: {e}")

    # In-memory fallback
    active_key = _get_store_key("users", plan.uid, "meal_plans", "active")
    history_key = _get_store_key("users", plan.uid, "meal_plans", plan.plan_id)
    plan_data = plan.model_dump(mode="json")
    _local_store[active_key] = plan_data
    _local_store[history_key] = plan_data
    logger.info(f"Saved meal plan to in-memory store: {plan.plan_id}")
    return True

def log_qa_interaction(uid: str, response: FoodQAResponse) -> bool:
    """Logs a food Q&A interaction to the user's history."""
    try:
        db = get_firestore_client()
        if db:
            history_ref = db.collection("users").document(uid).collection("qa_history").document()
            history_ref.set(response.model_dump(mode="json"))
            return True
    except Exception as e:
        logger.error(f"Firestore log_qa_interaction error: {e}")

    # In-memory fallback — just log it
    logger.info(f"Logged Q&A interaction in-memory for user {uid}: {response.query[:50]}")
    return True

import logging
from typing import Optional
from app.models.user import UserProfile, HealthProfile
from app.models.meal_plan import FullMealPlan
from app.models.food_qa import FoodQAQuery, FoodQAResponse
from app.agents.health_analyzer import analyze_health_and_tdee
from app.agents.meal_planner import generate_14_day_meal_plan
from app.agents.food_qa import answer_food_question
from app.tools.firestore_tools import get_user_profile, save_user_profile, get_health_profile, get_active_meal_plan

logger = logging.getLogger(__name__)

class NextBiteOrchestrator:
    """Master orchestrator connecting all sub-agents and tool state."""

    @staticmethod
    def get_or_create_user(uid: str, name: Optional[str] = None, email: Optional[str] = None) -> UserProfile:
        profile = get_user_profile(uid)
        if not profile:
            profile = UserProfile(
                uid=uid,
                name=name or "Alex Demo",
                email=email,
                age=30,
                weight_kg=75.0,
                height_cm=175.0,
                sex="male",
                goal="maintain",
                dietary_restrictions=[],
                fitness_user_id="1503960366"
            )
            save_user_profile(profile)
        return profile

    @classmethod
    def get_or_calculate_health_profile(cls, uid: str) -> HealthProfile:
        cached = get_health_profile(uid)
        if cached:
            return cached
        user = cls.get_or_create_user(uid)
        return analyze_health_and_tdee(user)

    @classmethod
    def handle_meal_plan_generation(cls, uid: str, force_regenerate: bool = False) -> FullMealPlan:
        user = cls.get_or_create_user(uid)
        health = cls.get_or_calculate_health_profile(uid)
        
        if not force_regenerate:
            existing = get_active_meal_plan(uid)
            if existing:
                return existing
                
        return generate_14_day_meal_plan(user, health)

    @classmethod
    def handle_food_qa(cls, uid: str, query: FoodQAQuery) -> FoodQAResponse:
        user = cls.get_or_create_user(uid)
        health = cls.get_or_calculate_health_profile(uid)
        return answer_food_question(user, health, query)

orchestrator = NextBiteOrchestrator()

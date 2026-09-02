from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from app.models.user import UserProfile, HealthProfile, MacroBreakdown
from app.tools.bigquery_tools import query_fitness_metrics
from app.tools.firestore_tools import save_health_profile

logger = logging.getLogger(__name__)

def calculate_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> int:
    """Calculates Basal Metabolic Rate using Mifflin-St Jeor equation."""
    if sex.lower() == "female":
        return int((10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161)
    else:
        return int((10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5)

def analyze_health_and_tdee(user_profile: UserProfile, fitness_data: Optional[List[Dict[str, Any]]] = None) -> HealthProfile:
    """
    Computes BMR, TDEE, activity classification, macro targets, and health insights.
    """
    # 1. Fetch fitness data from BigQuery if not provided
    if fitness_data is None:
        fitness_data = query_fitness_metrics(user_profile.fitness_user_id, limit_days=30)
    
    # 2. Compute averages from fitness records (or fallback to defaults)
    if fitness_data and len(fitness_data) > 0:
        steps_list = [r.get("total_steps", 0) for r in fitness_data if r.get("total_steps") is not None]
        avg_steps = int(sum(steps_list) / len(steps_list)) if steps_list else 8500
        
        sleep_list = [r.get("total_minutes_asleep", 0) for r in fitness_data if r.get("total_minutes_asleep")]
        avg_sleep_hours = round((sum(sleep_list) / len(sleep_list)) / 60.0, 1) if sleep_list else 7.2
        
        hr_list = [r.get("resting_heart_rate", 0) for r in fitness_data if r.get("resting_heart_rate")]
        avg_resting_hr = int(sum(hr_list) / len(hr_list)) if hr_list else 64
    else:
        avg_steps = 9200
        avg_sleep_hours = 7.3
        avg_resting_hr = 62

    # 3. Determine activity level & multiplier
    if avg_steps < 5000:
        activity_level = "sedentary"
        multiplier = 1.2
    elif avg_steps < 7500:
        activity_level = "lightly_active"
        multiplier = 1.375
    elif avg_steps < 11000:
        activity_level = "moderately_active"
        multiplier = 1.55
    elif avg_steps < 14000:
        activity_level = "very_active"
        multiplier = 1.725
    else:
        activity_level = "extra_active"
        multiplier = 1.9

    # 4. Calculate BMR and TDEE
    bmr = calculate_bmr(user_profile.weight_kg, user_profile.height_cm, user_profile.age, user_profile.sex)
    tdee = int(bmr * multiplier)

    # 5. Adjust target calories based on user goal
    goal = user_profile.goal.lower()
    if goal == "weight_loss":
        target_calories = max(1200, tdee - 500)
        protein_ratio, fat_ratio, carbs_ratio = 0.35, 0.25, 0.40
    elif goal == "muscle_gain":
        target_calories = tdee + 350
        protein_ratio, fat_ratio, carbs_ratio = 0.30, 0.25, 0.45
    elif goal == "endurance":
        target_calories = tdee + 200
        protein_ratio, fat_ratio, carbs_ratio = 0.25, 0.25, 0.50
    else:  # maintain
        target_calories = tdee
        protein_ratio, fat_ratio, carbs_ratio = 0.30, 0.30, 0.40

    # 6. Calculate target macronutrients (g)
    protein_g = int((target_calories * protein_ratio) / 4)
    fat_g = int((target_calories * fat_ratio) / 9)
    carbs_g = int((target_calories * carbs_ratio) / 4)

    macros = MacroBreakdown(
        calories=target_calories,
        protein_g=protein_g,
        carbs_g=carbs_g,
        fat_g=fat_g,
        fiber_g=32,
        sugar_limit_g=35,
        sodium_limit_mg=2300
    )

    # 7. Generate actionable insights
    insights = [
        f"Base BMR is {bmr} kcal/day; your estimated TDEE with {avg_steps:,} avg daily steps is {tdee} kcal.",
        f"Goal '{goal.replace('_', ' ').title()}' targets {target_calories} kcal/day ({protein_g}g Protein, {carbs_g}g Carbs, {fat_g}g Healthy Fats).",
        f"Resting heart rate averages {avg_resting_hr} bpm and sleep averages {avg_sleep_hours} hrs/night."
    ]

    profile = HealthProfile(
        uid=user_profile.uid,
        bmr=bmr,
        tdee=tdee,
        target_calories=target_calories,
        activity_level=activity_level,
        avg_daily_steps=avg_steps,
        avg_resting_hr=avg_resting_hr,
        avg_sleep_hours=avg_sleep_hours,
        recommended_macros=macros,
        insights=insights,
        calculated_at=datetime.utcnow()
    )

    # Save to Firestore
    save_health_profile(profile)
    return profile

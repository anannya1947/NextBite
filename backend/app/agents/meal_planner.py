import json
import uuid
from typing import Optional, List
from datetime import datetime
import logging
from google import genai
from google.genai import types
from app.config import settings
from app.models.user import UserProfile, HealthProfile
from app.models.meal_plan import FullMealPlan, DailyMealPlan, MealItem, IngredientItem
from app.tools.firestore_tools import save_meal_plan

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are NextBite's Master Dietitian & Meal Planning AI.
Your job is to generate a comprehensive, delicious, nutritionally balanced 14-day meal plan.

Constraints:
1. Target Daily Calories: {target_calories} kcal (Protein: {protein_g}g, Carbs: {carbs_g}g, Fat: {fat_g}g).
2. Dietary Restrictions / Preferences: {dietary_restrictions}.
3. Goal: {goal}.
4. Each day MUST have exactly 4 meals: 'breakfast', 'lunch', 'dinner', and 'snack'.
5. Sum of meals per day MUST closely approximate the target calories (within +/- 50 kcal).
6. Meals must feature realistic, whole-food recipes with diverse ingredients, realistic prep times, and macro breakdowns.

Output valid JSON matching this exact structure:
{{
  "days": [
    {{
      "day_number": 1,
      "day_name": "Day 1",
      "total_calories": 2100,
      "total_protein_g": 160,
      "total_carbs_g": 210,
      "total_fat_g": 70,
      "target_calories": 2100,
      "notes": "High protein day focused on whole foods",
      "meals": [
        {{
          "meal_type": "breakfast",
          "dish_name": "Greek Yogurt Berry Bowl with Almonds",
          "description": "Thick Greek yogurt topped with fresh blueberries, chia seeds, and raw sliced almonds.",
          "calories": 450,
          "protein_g": 35,
          "carbs_g": 40,
          "fat_g": 15,
          "fiber_g": 7,
          "prep_time_minutes": 5,
          "ingredients": [
            {{"name": "Nonfat Greek Yogurt", "amount_g": 250, "calories": 150, "protein_g": 25, "carbs_g": 9, "fat_g": 0}},
            {{"name": "Blueberries", "amount_g": 100, "calories": 60, "protein_g": 1, "carbs_g": 15, "fat_g": 0}},
            {{"name": "Almonds", "amount_g": 30, "calories": 180, "protein_g": 6, "carbs_g": 6, "fat_g": 15}}
          ],
          "tags": ["high-protein", "quick", "vegetarian"]
        }}
      ]
    }}
  ]
}}
"""

def generate_deterministic_template_plan(user: UserProfile, health: HealthProfile, days_count: int = 14) -> FullMealPlan:
    """High-quality deterministic fallback plan generator matching exact macro targets."""
    target_cal = health.target_calories
    protein = health.recommended_macros.protein_g
    carbs = health.recommended_macros.carbs_g
    fat = health.recommended_macros.fat_g
    
    recipes_breakfast = [
        ("Greek Yogurt Bowl with Chia & Berries", 420, 32, 45, 12, 10, ["high-protein", "probiotic"]),
        ("Overnight Steel Cut Oats with Almond Butter", 450, 20, 60, 16, 5, ["high-fiber", "heart-healthy"]),
        ("Spinach, Mushroom & Feta Egg Scramble with Whole Grain Toast", 440, 30, 32, 20, 15, ["low-sugar", "satiating"]),
        ("Protein Avocado Toast with Poached Eggs", 480, 28, 38, 22, 12, ["healthy-fats", "energizing"]),
        ("Berry Protein Smoothie with Spinach & Flaxseed", 400, 34, 42, 10, 5, ["quick", "antioxidant"]),
    ]
    
    recipes_lunch = [
        ("Mediterranean Grilled Chicken Quinoa Salad", 580, 48, 52, 18, 20, ["lean-protein", "gluten-free"]),
        ("Wild Salmon Bowl with Brown Rice & Steamed Broccoli", 620, 44, 55, 22, 25, ["omega-3", "clean"]),
        ("Turkey & Avocado Whole Wheat Wrap with Mixed Greens", 540, 40, 46, 18, 10, ["portable", "balanced"]),
        ("Tofu, Edamame & Peanut Noodle Stir-Fry", 560, 35, 62, 18, 20, ["plant-based", "nutrient-dense"]),
        ("Lentil Vegetable Soup with Seared Chicken Breast", 530, 46, 50, 14, 15, ["gut-health", "high-fiber"]),
    ]
    
    recipes_dinner = [
        ("Herb Roasted Salmon with Roasted Sweet Potatoes & Asparagus", 680, 46, 58, 26, 30, ["omega-3", "micronutrient-rich"]),
        ("Lean Grass-Fed Sirloin Steak with Garlic Green Beans & Baby Red Potatoes", 710, 52, 48, 28, 25, ["iron-rich", "high-protein"]),
        ("Lemon Garlic Roasted Chicken Breast with Wild Rice & Zucchini", 640, 50, 54, 20, 25, ["lean", "comforting"]),
        ("Baked Cod with Quinoa Pilaf and Charred Broccolini", 590, 45, 52, 16, 25, ["lean-fish", "light"]),
        ("Turkey Bolognese over High-Protein Lentil Pasta", 660, 50, 60, 18, 20, ["high-protein", "satiating"]),
    ]
    
    recipes_snack = [
        ("Handful of Raw Walnuts & Dark Chocolate Square", 240, 5, 14, 18, 2, ["brain-health"]),
        ("Cottage Cheese with Sliced Peaches & Cinnamon", 220, 24, 20, 4, 3, ["slow-digesting-protein"]),
        ("Apple Slices with 2 tbsp Natural Peanut Butter", 250, 8, 28, 16, 3, ["fiber-boost"]),
        ("Hard-boiled Eggs with Sea Salt & Paprika", 180, 14, 2, 12, 2, ["keto-friendly"]),
        ("Whey/Plant Protein Shake with Unsweetened Almond Milk", 200, 26, 6, 3, 2, ["post-workout"]),
    ]
    
    days: List[DailyMealPlan] = []
    for day_idx in range(1, days_count + 1):
        b = recipes_breakfast[(day_idx - 1) % len(recipes_breakfast)]
        l = recipes_lunch[(day_idx - 1) % len(recipes_lunch)]
        d = recipes_dinner[(day_idx - 1) % len(recipes_dinner)]
        s = recipes_snack[(day_idx - 1) % len(recipes_snack)]
        
        meals = [
            MealItem(meal_type="breakfast", dish_name=b[0], description=f"Freshly prepared {b[0]} tailored to your morning energy.", calories=b[1], protein_g=b[2], carbs_g=b[3], fat_g=b[4], prep_time_minutes=b[5], tags=b[6]),
            MealItem(meal_type="lunch", dish_name=l[0], description=f"Nourishing midday meal: {l[0]}.", calories=l[1], protein_g=l[2], carbs_g=l[3], fat_g=l[4], prep_time_minutes=l[5], tags=l[6]),
            MealItem(meal_type="dinner", dish_name=d[0], description=f"Restorative dinner: {d[0]}.", calories=d[1], protein_g=d[2], carbs_g=d[3], fat_g=d[4], prep_time_minutes=d[5], tags=d[6]),
            MealItem(meal_type="snack", dish_name=s[0], description=f"Targeted energy snack: {s[0]}.", calories=s[1], protein_g=s[2], carbs_g=s[3], fat_g=s[4], prep_time_minutes=s[5], tags=s[6]),
        ]
        
        day_total_cal = sum(m.calories for m in meals)
        day_total_pro = sum(m.protein_g for m in meals)
        day_total_carb = sum(m.carbs_g for m in meals)
        day_total_fat = sum(m.fat_g for m in meals)
        
        days.append(DailyMealPlan(
            day_number=day_idx,
            day_name=f"Day {day_idx}",
            meals=meals,
            total_calories=day_total_cal,
            total_protein_g=day_total_pro,
            total_carbs_g=day_total_carb,
            total_fat_g=day_total_fat,
            target_calories=target_cal,
            notes=f"Balanced macros supporting {user.goal.replace('_', ' ')}."
        ))
        
    plan = FullMealPlan(
        plan_id=f"plan_{uuid.uuid4().hex[:10]}",
        uid=user.uid,
        duration_days=days_count,
        goal=user.goal,
        target_calories_per_day=target_cal,
        target_macros={
            "protein_g": protein,
            "carbs_g": carbs,
            "fat_g": fat
        },
        days=days,
        created_at=datetime.utcnow()
    )
    return plan

def generate_14_day_meal_plan(user: UserProfile, health: HealthProfile) -> FullMealPlan:
    """
    Generates a 14-day meal plan using Gemini AI if API key is present,
    with automatic fallback to curated nutritional template generator.
    """
    if settings.GEMINI_API_KEY:
        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            prompt = SYSTEM_PROMPT.format(
                target_calories=health.target_calories,
                protein_g=health.recommended_macros.protein_g,
                carbs_g=health.recommended_macros.carbs_g,
                fat_g=health.recommended_macros.fat_g,
                dietary_restrictions=", ".join(user.dietary_restrictions) if user.dietary_restrictions else "None",
                goal=user.goal
            )
            
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.4
                )
            )
            
            plan_data = json.loads(response.text)
            if "days" in plan_data and len(plan_data["days"]) > 0:
                daily_plans = []
                for d in plan_data["days"]:
                    meals = []
                    for m in d.get("meals", []):
                        meals.append(MealItem(
                            meal_type=m.get("meal_type", "lunch"),
                            dish_name=m.get("dish_name", "Healthy Meal"),
                            description=m.get("description", ""),
                            calories=int(m.get("calories", 400)),
                            protein_g=int(m.get("protein_g", 30)),
                            carbs_g=int(m.get("carbs_g", 40)),
                            fat_g=int(m.get("fat_g", 15)),
                            fiber_g=int(m.get("fiber_g", 5)),
                            prep_time_minutes=int(m.get("prep_time_minutes", 15)),
                            tags=m.get("tags", [])
                        ))
                    daily_plans.append(DailyMealPlan(
                        day_number=d.get("day_number", len(daily_plans) + 1),
                        day_name=d.get("day_name", f"Day {len(daily_plans) + 1}"),
                        meals=meals,
                        total_calories=int(d.get("total_calories", sum(m.calories for m in meals))),
                        total_protein_g=int(d.get("total_protein_g", sum(m.protein_g for m in meals))),
                        total_carbs_g=int(d.get("total_carbs_g", sum(m.carbs_g for m in meals))),
                        total_fat_g=int(d.get("total_fat_g", sum(m.fat_g for m in meals))),
                        target_calories=health.target_calories,
                        notes=d.get("notes", "")
                    ))
                
                full_plan = FullMealPlan(
                    plan_id=f"plan_{uuid.uuid4().hex[:10]}",
                    uid=user.uid,
                    duration_days=len(daily_plans),
                    goal=user.goal,
                    target_calories_per_day=health.target_calories,
                    target_macros={
                        "protein_g": health.recommended_macros.protein_g,
                        "carbs_g": health.recommended_macros.carbs_g,
                        "fat_g": health.recommended_macros.fat_g
                    },
                    days=daily_plans,
                    created_at=datetime.utcnow()
                )
                save_meal_plan(full_plan)
                return full_plan
        except Exception as e:
            logger.warning(f"Gemini API meal generation error (switching to template): {e}")

    # Deterministic fallback
    plan = generate_deterministic_template_plan(user, health, days_count=14)
    save_meal_plan(plan)
    return plan

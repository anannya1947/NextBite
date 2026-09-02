from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

class IngredientItem(BaseModel):
    name: str
    amount_g: float
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float

class MealItem(BaseModel):
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    dish_name: str
    description: str
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    fiber_g: int = 0
    prep_time_minutes: int = 15
    ingredients: List[IngredientItem] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

class DailyMealPlan(BaseModel):
    day_number: int
    day_name: str
    meals: List[MealItem]
    total_calories: int
    total_protein_g: int
    total_carbs_g: int
    total_fat_g: int
    target_calories: int
    notes: Optional[str] = None

class FullMealPlan(BaseModel):
    plan_id: str
    uid: str
    duration_days: int = 14
    goal: str
    target_calories_per_day: int
    target_macros: dict
    days: List[DailyMealPlan]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1

class PlanRegenerateRequest(BaseModel):
    day_number: Optional[int] = None
    meal_type: Optional[str] = None
    preferences_override: Optional[List[str]] = None

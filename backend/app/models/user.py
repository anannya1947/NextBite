from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

class UserProfile(BaseModel):
    uid: str
    name: str = "Alex Demo"
    email: Optional[str] = None
    age: int = Field(default=30, ge=12, le=120)
    weight_kg: float = Field(default=75.0, ge=30.0, le=300.0)
    height_cm: float = Field(default=175.0, ge=100.0, le=250.0)
    sex: Literal["male", "female", "other"] = "male"
    goal: Literal["weight_loss", "muscle_gain", "maintain", "endurance"] = "maintain"
    dietary_restrictions: List[str] = Field(default_factory=list)
    fitness_user_id: str = "1503960366"  # ID from Fitbit dataset
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MacroBreakdown(BaseModel):
    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int
    fiber_g: int = 30
    sugar_limit_g: int = 40
    sodium_limit_mg: int = 2300

class HealthProfile(BaseModel):
    uid: str
    bmr: int
    tdee: int
    target_calories: int
    activity_level: Literal["sedentary", "lightly_active", "moderately_active", "very_active", "extra_active"]
    avg_daily_steps: int
    avg_resting_hr: int
    avg_sleep_hours: float
    recommended_macros: MacroBreakdown
    insights: List[str]
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class FoodQAQuery(BaseModel):
    query: str
    meal_type: Optional[str] = "snack"
    context_portion: Optional[str] = "1 serving"

class NutritionContext(BaseModel):
    food_name: str
    serving_size: str
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    sugar_g: float = 0.0
    sodium_mg: float = 0.0

class FoodQAResponse(BaseModel):
    query: str
    verdict_summary: str
    tone_verdict: str  # "encouraging", "supportive_caution", "celebratory"
    nutrition_facts: Optional[NutritionContext] = None
    impact_analysis: str
    tradeoffs_and_adjustments: List[str]
    healthy_alternatives: List[str]
    suggested_balance_action: str
    timestamp: datetime = datetime.utcnow()

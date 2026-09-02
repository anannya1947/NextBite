from typing import List, Optional
from pydantic import BaseModel
from datetime import date

class DailyFitnessRecord(BaseModel):
    activity_date: str
    total_steps: int
    total_distance: float
    calories_burned: int
    very_active_minutes: int
    fairly_active_minutes: int
    lightly_active_minutes: int
    sedentary_minutes: int
    total_minutes_asleep: Optional[int] = None
    total_time_in_bed: Optional[int] = None
    avg_heart_rate: Optional[int] = None
    resting_heart_rate: Optional[int] = None

class FitnessSummary(BaseModel):
    user_id: str
    period_days: int
    avg_steps: int
    avg_calories: int
    avg_sleep_minutes: int
    avg_resting_hr: int
    active_days_count: int
    latest_record: Optional[DailyFitnessRecord] = None

class FitnessTrend(BaseModel):
    dates: List[str]
    steps: List[int]
    calories: List[int]
    sleep_hours: List[float]
    resting_hr: List[int]

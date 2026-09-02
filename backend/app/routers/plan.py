from fastapi import APIRouter, Depends, HTTPException, Query
from app.auth import get_current_user, AuthenticatedUser
from app.models.meal_plan import FullMealPlan, PlanRegenerateRequest
from app.agents.orchestrator import orchestrator
from app.tools.firestore_tools import get_active_meal_plan

router = APIRouter(prefix="/api/plan", tags=["Meal Planning"])

@router.post("/generate", response_model=FullMealPlan, summary="Generate a fresh 14-day personalized meal plan")
async def generate_meal_plan(
    force_new: bool = Query(default=False),
    user: AuthenticatedUser = Depends(get_current_user)
):
    return orchestrator.handle_meal_plan_generation(user.uid, force_regenerate=force_new)

@router.get("/latest", response_model=FullMealPlan, summary="Get the user's latest active meal plan")
async def get_latest_meal_plan(user: AuthenticatedUser = Depends(get_current_user)):
    plan = get_active_meal_plan(user.uid)
    if not plan:
        # Generate automatically on first visit
        return orchestrator.handle_meal_plan_generation(user.uid, force_regenerate=False)
    return plan

@router.post("/regenerate", response_model=FullMealPlan, summary="Regenerate meal plan with updated constraints")
async def regenerate_plan(
    request: PlanRegenerateRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    # Generates a refreshed plan aligned with latest targets
    return orchestrator.handle_meal_plan_generation(user.uid, force_regenerate=True)

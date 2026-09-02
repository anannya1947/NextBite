from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_user, AuthenticatedUser
from app.models.user import HealthProfile, UserProfile
from app.agents.orchestrator import orchestrator
from app.agents.health_analyzer import analyze_health_and_tdee
from app.tools.firestore_tools import save_user_profile

router = APIRouter(prefix="/api/health", tags=["Health & Analytics"])

@router.get("", summary="Service Health Check")
async def health_check():
    return {
        "status": "healthy",
        "service": "NextBite Backend API",
        "version": "1.0.0"
    }

@router.get("/profile", response_model=HealthProfile, summary="Get calculated health & TDEE profile")
async def get_health_profile_endpoint(user: AuthenticatedUser = Depends(get_current_user)):
    return orchestrator.get_or_calculate_health_profile(user.uid)

@router.post("/recalculate", response_model=HealthProfile, summary="Recalculate TDEE and health profile")
async def recalculate_health_profile(user: AuthenticatedUser = Depends(get_current_user)):
    user_profile = orchestrator.get_or_create_user(user.uid, user.name, user.email)
    return analyze_health_and_tdee(user_profile)

@router.post("/profile/update", response_model=HealthProfile, summary="Update user metrics & recalculate")
async def update_user_metrics(profile_data: UserProfile, user: AuthenticatedUser = Depends(get_current_user)):
    profile_data.uid = user.uid
    save_user_profile(profile_data)
    return analyze_health_and_tdee(profile_data)

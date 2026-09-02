from fastapi import APIRouter, Depends
from typing import List
from app.auth import get_current_user, AuthenticatedUser
from app.models.food_qa import FoodQAQuery, FoodQAResponse
from app.agents.orchestrator import orchestrator
from app.config import settings

router = APIRouter(prefix="/api/voice", tags=["Voice & Food Q&A"])

@router.post("/ask", response_model=FoodQAResponse, summary="Ask if a food item is okay to eat")
async def ask_food_question(
    query: FoodQAQuery,
    user: AuthenticatedUser = Depends(get_current_user)
):
    return orchestrator.handle_food_qa(user.uid, query)

@router.get("/suggestions", response_model=List[str], summary="Get starter questions for voice interaction")
async def get_voice_suggestions():
    return [
        "I'm having a salad with grilled chicken and olive oil for lunch",
        "Is two slices of pepperoni pizza okay for dinner?",
        "Can I have a chocolate milkshake after my workout?",
        "I want oatmeal with banana and peanut butter for breakfast",
        "What about a double cheeseburger with fries?"
    ]

@router.post("/token", summary="Generate Gemini session info for Live audio relay")
async def get_live_voice_session(user: AuthenticatedUser = Depends(get_current_user)):
    return {
        "status": "ready",
        "model": settings.GEMINI_MODEL,
        "session_mode": "voice_relay",
        "relay_endpoint": "/api/voice/ask",
        "user_id": user.uid
    }

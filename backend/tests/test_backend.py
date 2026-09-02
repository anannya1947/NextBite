import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import UserProfile
from app.agents.health_analyzer import calculate_bmr, analyze_health_and_tdee
from app.agents.nutrition_rag import lookup_nutrition_rag
from app.agents.food_qa import answer_food_question
from app.models.food_qa import FoodQAQuery

client = TestClient(app)

def test_health_check_endpoint():
    """Verify health endpoint returns 200 and healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "NextBite" in data["service"]

def test_security_headers():
    """Verify security headers are applied to HTTP responses."""
    response = client.get("/api/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"

def test_mifflin_st_jeor_bmr():
    """Verify BMR calculation for male and female."""
    # Male: (10 * 75) + (6.25 * 175) - (5 * 30) + 5 = 750 + 1093.75 - 150 + 5 = 1698.75 -> 1698
    bmr_male = calculate_bmr(75.0, 175.0, 30, "male")
    assert 1690 <= bmr_male <= 1710

    # Female: (10 * 60) + (6.25 * 165) - (5 * 25) - 161 = 600 + 1031.25 - 125 - 161 = 1345.25 -> 1345
    bmr_female = calculate_bmr(60.0, 165.0, 25, "female")
    assert 1340 <= bmr_female <= 1350

def test_health_analyzer_tdee():
    """Verify TDEE and macro distribution for weight loss and muscle gain."""
    user = UserProfile(
        uid="test-user-1",
        name="Tester",
        age=30,
        weight_kg=75.0,
        height_cm=175.0,
        sex="male",
        goal="weight_loss"
    )
    health = analyze_health_and_tdee(user)
    assert health.target_calories < health.tdee
    assert health.recommended_macros.protein_g > 100
    assert health.recommended_macros.calories == health.target_calories

def test_nutrition_rag_lookup():
    """Verify USDA / RAG food lookup returns valid nutritional facts."""
    results = lookup_nutrition_rag("chicken breast")
    assert len(results) > 0
    top = results[0]
    assert "protein_g" in top
    assert top["calories"] > 0

def test_food_qa_tone_and_grounding():
    """Verify Food Q&A answers without blunt yes/no and provides actionable advice."""
    user = UserProfile(uid="test-qa", goal="maintain")
    health = analyze_health_and_tdee(user)
    query = FoodQAQuery(query="Is a grilled chicken salad with olive oil good for lunch?")
    
    answer = answer_food_question(user, health, query)
    assert answer.verdict_summary
    assert len(answer.tradeoffs_and_adjustments) > 0
    assert answer.tone_verdict in ["encouraging", "supportive_caution", "celebratory"]

def test_meal_plan_endpoint_dev_auth():
    """Verify meal plan generation endpoint works with dev user context."""
    response = client.post("/api/plan/generate?force_new=false", headers={"X-Dev-User-Id": "demo-user-001"})
    assert response.status_code == 200
    plan = response.json()
    assert len(plan["days"]) == 14
    assert plan["target_calories_per_day"] > 1000
    assert len(plan["days"][0]["meals"]) == 4

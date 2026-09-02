import json
from typing import Optional
from datetime import datetime
import logging
from google import genai
from google.genai import types
from app.config import settings
from app.models.user import UserProfile, HealthProfile
from app.models.food_qa import FoodQAQuery, FoodQAResponse, NutritionContext
from app.agents.nutrition_rag import lookup_nutrition_rag, format_nutrition_context_for_prompt
from app.tools.firestore_tools import log_qa_interaction

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are NextBite's empathetic, certified nutrition advisor and food Q&A agent.
A user asks if a specific food is okay to eat in their daily routine.

Your Core Guiding Philosophy:
1. NEVER give a blunt "No" or "Yes". Food is not morally good or bad.
2. Contextualize the food relative to their daily budget ({target_calories} kcal/day, {protein_g}g protein target) and goal ({goal}).
3. Acknowledge and affirm if the food is nutrient-dense and fits well.
4. If the food is calorie-dense or high in saturated fats/sugars, explain its impact constructively and suggest 1-2 realistic modifications or balanced swaps without inducing guilt.
5. Suggest a realistic balancing action (e.g. enjoying a slightly lighter dinner, drinking an extra glass of water, taking a brisk 15-minute walk).

FACTUAL NUTRITION REFERENCE FROM USDA FOOD DATABASE:
{nutrition_rag_context}

Return a valid JSON object matching this schema:
{{
  "verdict_summary": "Short 1-sentence supportive verdict",
  "tone_verdict": "encouraging" | "supportive_caution" | "celebratory",
  "impact_analysis": "2-3 sentences explaining calorie and macro impact against their daily goal",
  "tradeoffs_and_adjustments": [
    "Tip 1: e.g. Pairing with a lean protein source",
    "Tip 2: e.g. Adjusting dinner carbs"
  ],
  "healthy_alternatives": [
    "Alternative 1",
    "Alternative 2"
  ],
  "suggested_balance_action": "e.g. A 20-minute evening walk or lighter lunch"
}}
"""

def answer_food_question(
    user: UserProfile,
    health: HealthProfile,
    query_data: FoodQAQuery
) -> FoodQAResponse:
    """Answers user food inquiry with RAG grounded data and empathetic guidance."""
    # 1. RAG lookup from USDA BigQuery / local cache
    rag_foods = lookup_nutrition_rag(query_data.query, limit=3)
    primary_fact = rag_foods[0] if rag_foods else None
    rag_context_text = format_nutrition_context_for_prompt(rag_foods)
    
    nut_context = None
    if primary_fact:
        nut_context = NutritionContext(
            food_name=primary_fact["description"],
            serving_size=query_data.context_portion or "100g",
            calories=int(primary_fact.get("calories", 0)),
            protein_g=float(primary_fact.get("protein_g", 0.0)),
            carbs_g=float(primary_fact.get("carbs_g", 0.0)),
            fat_g=float(primary_fact.get("fat_g", 0.0)),
            sugar_g=float(primary_fact.get("sugar_g", 0.0)),
            sodium_mg=float(primary_fact.get("sodium_mg", 0.0)),
        )

    # 2. Try Gemini API
    if settings.GEMINI_API_KEY:
        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            prompt = SYSTEM_PROMPT.format(
                target_calories=health.target_calories,
                protein_g=health.recommended_macros.protein_g,
                goal=user.goal.replace('_', ' '),
                nutrition_rag_context=rag_context_text
            ) + f"\n\nUser Question: '{query_data.query}' (Meal: {query_data.meal_type}, Portion: {query_data.context_portion})"

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3
                )
            )

            data = json.loads(response.text)
            qa_res = FoodQAResponse(
                query=query_data.query,
                verdict_summary=data.get("verdict_summary", "Here is how this food fits into your nutrition plan."),
                tone_verdict=data.get("tone_verdict", "encouraging"),
                nutrition_facts=nut_context,
                impact_analysis=data.get("impact_analysis", ""),
                tradeoffs_and_adjustments=data.get("tradeoffs_and_adjustments", []),
                healthy_alternatives=data.get("healthy_alternatives", []),
                suggested_balance_action=data.get("suggested_balance_action", "Stay hydrated and enjoy your meal!"),
                timestamp=datetime.utcnow()
            )
            log_qa_interaction(user.uid, qa_res)
            return qa_res
        except Exception as e:
            logger.warning(f"Gemini Food Q&A error (using grounded fallback rule engine): {e}")

    # 3. Rule-based grounded fallback response
    cal = nut_context.calories if nut_context else 250
    pct = round((cal / health.target_calories) * 100)
    
    if cal < 200:
        verdict = f"Absolutely! At ~{cal} kcal, this is a light, nutrient-friendly option."
        tone = "encouraging"
        adjustments = ["Great choice for sustained energy without heavy caloric load."]
        alts = ["Fresh fruit bowl", "Cucumber slices with hummus"]
        balance = "No adjustments needed—fits right into your target budget."
    elif cal <= 450:
        verdict = f"Yes, this fits smoothly into your meal budget (~{cal} kcal, ~{pct}% of daily energy)."
        tone = "encouraging"
        adjustments = ["Pair with a serving of green veggies or extra water for satiety."]
        alts = ["Grilled protein wrap", "Quinoa bowl with avocado"]
        balance = "Keeps your daily macro targets well on track."
    else:
        verdict = f"You can certainly enjoy it! Just keep in mind it provides ~{cal} kcal (~{pct}% of your daily budget)."
        tone = "supportive_caution"
        adjustments = ["Consider a slightly lighter dinner or saving half for later.", "Opt for water or unsweetened tea to avoid added liquid sugars."]
        alts = ["Air-fried or grilled version with side salad", "Single portion with double vegetables"]
        balance = "A relaxing 20-minute evening walk will help maintain your daily balance effortlessly."

    qa_res = FoodQAResponse(
        query=query_data.query,
        verdict_summary=verdict,
        tone_verdict=tone,
        nutrition_facts=nut_context,
        impact_analysis=f"This food provides approximately {cal} kcal toward your daily target of {health.target_calories} kcal ({pct}% of total daily intake).",
        tradeoffs_and_adjustments=adjustments,
        healthy_alternatives=alts,
        suggested_balance_action=balance,
        timestamp=datetime.utcnow()
    )
    log_qa_interaction(user.uid, qa_res)
    return qa_res

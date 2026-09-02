from typing import List, Dict, Any, Optional
import logging
from app.tools.bigquery_tools import search_usda_foods

logger = logging.getLogger(__name__)

# Fallback reference foods dictionary for instant grounding
CORE_NUTRITION_LOOKUP = {
    "chicken breast": {"calories": 165, "protein_g": 31.0, "fat_g": 3.6, "carbs_g": 0.0, "fiber_g": 0.0, "sugar_g": 0.0, "sodium_mg": 74.0},
    "salmon": {"calories": 208, "protein_g": 20.4, "fat_g": 13.4, "carbs_g": 0.0, "fiber_g": 0.0, "sugar_g": 0.0, "sodium_mg": 59.0},
    "brown rice": {"calories": 112, "protein_g": 2.6, "fat_g": 0.9, "carbs_g": 23.5, "fiber_g": 1.8, "sugar_g": 0.2, "sodium_mg": 5.0},
    "quinoa": {"calories": 120, "protein_g": 4.4, "fat_g": 1.9, "carbs_g": 21.3, "fiber_g": 2.8, "sugar_g": 0.9, "sodium_mg": 7.0},
    "rolled oats": {"calories": 389, "protein_g": 16.9, "fat_g": 6.9, "carbs_g": 66.3, "fiber_g": 10.6, "sugar_g": 0.0, "sodium_mg": 2.0},
    "eggs": {"calories": 143, "protein_g": 12.6, "fat_g": 9.5, "carbs_g": 0.7, "fiber_g": 0.0, "sugar_g": 0.4, "sodium_mg": 142.0},
    "greek yogurt": {"calories": 59, "protein_g": 10.2, "fat_g": 0.4, "carbs_g": 3.6, "fiber_g": 0.0, "sugar_g": 3.2, "sodium_mg": 36.0},
    "avocado": {"calories": 160, "protein_g": 2.0, "fat_g": 14.7, "carbs_g": 8.5, "fiber_g": 6.7, "sugar_g": 0.7, "sodium_mg": 7.0},
    "spinach": {"calories": 23, "protein_g": 2.9, "fat_g": 0.4, "carbs_g": 3.6, "fiber_g": 2.2, "sugar_g": 0.4, "sodium_mg": 79.0},
    "broccoli": {"calories": 34, "protein_g": 2.8, "fat_g": 0.4, "carbs_g": 6.6, "fiber_g": 2.6, "sugar_g": 1.7, "sodium_mg": 33.0},
    "almonds": {"calories": 579, "protein_g": 21.2, "fat_g": 49.9, "carbs_g": 21.6, "fiber_g": 12.5, "sugar_g": 4.4, "sodium_mg": 1.0},
    "apple": {"calories": 52, "protein_g": 0.3, "fat_g": 0.2, "carbs_g": 13.8, "fiber_g": 2.4, "sugar_g": 10.4, "sodium_mg": 1.0},
    "banana": {"calories": 89, "protein_g": 1.1, "fat_g": 0.3, "carbs_g": 22.8, "fiber_g": 2.6, "sugar_g": 12.2, "sodium_mg": 1.0},
    "olive oil": {"calories": 884, "protein_g": 0.0, "fat_g": 100.0, "carbs_g": 0.0, "fiber_g": 0.0, "sugar_g": 0.0, "sodium_mg": 2.0},
    "sweet potato": {"calories": 86, "protein_g": 1.6, "fat_g": 0.1, "carbs_g": 20.1, "fiber_g": 3.0, "sugar_g": 4.2, "sodium_mg": 55.0},
    "pizza": {"calories": 266, "protein_g": 11.4, "fat_g": 9.8, "carbs_g": 33.3, "fiber_g": 2.3, "sugar_g": 3.6, "sodium_mg": 598.0},
    "milkshake": {"calories": 280, "protein_g": 6.2, "fat_g": 9.0, "carbs_g": 45.0, "fiber_g": 0.8, "sugar_g": 42.0, "sodium_mg": 160.0},
    "cheeseburger": {"calories": 303, "protein_g": 15.6, "fat_g": 14.2, "carbs_g": 28.5, "fiber_g": 1.5, "sugar_g": 5.1, "sodium_mg": 560.0},
}

def lookup_nutrition_rag(food_name: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    RAG retrieval: Queries BigQuery USDA foods first; falls back to curated standard facts.
    """
    # 1. Search BigQuery
    bq_results = search_usda_foods(food_name, limit=limit)
    if bq_results:
        return bq_results

    # 2. Fallback matching
    food_name_lower = food_name.lower().strip()
    matches = []
    for key, data in CORE_NUTRITION_LOOKUP.items():
        if key in food_name_lower or food_name_lower in key:
            matches.append({
                "fdc_id": f"ref-{key}",
                "description": key.title(),
                **data
            })
    
    if not matches:
        # Default placeholder per 100g estimation
        matches.append({
            "fdc_id": "ref-generic",
            "description": food_name.title(),
            "calories": 180,
            "protein_g": 8.0,
            "fat_g": 6.0,
            "carbs_g": 22.0,
            "fiber_g": 2.0,
            "sugar_g": 5.0,
            "sodium_mg": 150.0
        })
        
    return matches[:limit]

def format_nutrition_context_for_prompt(foods: List[Dict[str, Any]]) -> str:
    """Formats retrieved USDA food entries into a clear markdown table for LLM prompts."""
    lines = ["| Food Item | Calories (per 100g) | Protein | Fat | Carbs | Fiber | Sodium |",
             "|---|---|---|---|---|---|---|"]
    for f in foods:
        lines.append(f"| {f['description']} | {f['calories']} kcal | {f['protein_g']}g | {f['fat_g']}g | {f['carbs_g']}g | {f['fiber_g']}g | {f['sodium_mg']}mg |")
    return "\n".join(lines)

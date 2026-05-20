"""Prompt building for the Groq recommendation model."""

from __future__ import annotations

import json
from typing import Any
from src.phases.phase00.preferences import UserPreferences

SYSTEM_PROMPT = """You are an expert Zomato restaurant recommender system.
Your goal is to rank the candidate restaurants based on user preferences and return the top recommendations.

CRITICAL INSTRUCTIONS:
1. Grounding: You MUST ONLY recommend restaurants that are explicitly listed in the Candidate Restaurants list. Do not hallucinate, make up, or suggest any restaurant that is not in the candidates list.
2. Output Format: You MUST respond with a single JSON object. Do not output any markdown blocks (like ```json ... ```) or conversational filler around the JSON.
3. Schema: The JSON object must conform to the following schema:
{
  "recommendations": [
    {
      "name": "Exact restaurant name matching the candidate list",
      "cuisine": "Cuisine type (optional/matching data)",
      "rating": 4.2,
      "estimated_cost": 500,
      "explanation": "A personalized, compelling 1-2 sentence explanation of why this restaurant fits the user preferences."
    }
  ],
  "summary": "A 2-3 sentence overview explaining why these top recommendations are the absolute best match for the user."
}
"""

def build_user_prompt(prefs: UserPreferences, candidates: list[dict[str, Any]], top_k: int = 5) -> str:
    """Formulate the user prompt injecting preferences and candidates list."""
    # Filter candidates to only include key fields to save tokens
    clean_candidates = []
    for c in candidates:
        clean_candidates.append({
            "name": c.get("name"),
            "cuisines": c.get("cuisines"),
            "rating": c.get("rating"),
            "cost_for_two": c.get("cost_for_two"),
            "budget_tier": c.get("budget_tier"),
            "location": c.get("location"),
            "rest_type": c.get("rest_type"),
            "book_table": c.get("book_table"),
            "online_order": c.get("online_order"),
            "dish_liked": c.get("dish_liked"),
        })

    user_info = {
        "city": prefs.city,
        "budget_tier": prefs.budget,
        "cuisines": prefs.cuisines,
        "min_rating": prefs.min_rating,
        "extras": {
            "family_friendly": prefs.extras.family_friendly,
            "quick_service": prefs.extras.quick_service,
            "book_table": prefs.extras.book_table,
        },
        "additional_notes": prefs.additional_notes,
    }

    return f"""User Preferences:
{json.dumps(user_info, indent=2)}

Candidate Restaurants (Total: {len(candidates)}):
{json.dumps(clean_candidates, indent=2)}

Generate the top {top_k} recommendations matching the user's preferences from the candidate list above. Return ONLY the JSON object.
"""

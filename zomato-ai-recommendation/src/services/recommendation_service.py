"""Service to coordinate filtering and LLM recommendation."""

from __future__ import annotations

import logging
from typing import Any, Optional
import pandas as pd

from src.config import TOP_K_RECOMMENDATIONS
from src.phases.phase00.preferences import UserPreferences
from src.phases.phase00.output_contract import RecommendationItem, RecommendationResponse
from src.phases.phase02 import FilterEngine
from src.phases.phase02.payloads import to_llm_payload
from src.llm.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.llm.client import complete
from src.llm.parser import parse_llm_json, drop_unknown_names, enrich_from_dataframe
from src.config import get_llm_api_key

logger = logging.getLogger(__name__)


def _to_bool(val: Any) -> bool:
    """Convert string 'Yes'/'No' or bool-like values to Python bool."""
    if isinstance(val, bool):
        return val
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    return str(val).strip().casefold() in {"yes", "y", "true", "1"}

class RecommendationService:
    """Orchestrates candidate filtering and LLM ranking & explanation."""

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df
        self.filter_engine = FilterEngine(df)

    def recommend(self, prefs: UserPreferences, top_k: Optional[int] = None) -> RecommendationResponse:
        """
        Produce personalized recommendations based on preferences.
        Runs candidates through FilterEngine, and then ranks & explains them via LLM.
        Falls back to scorer-based sorting if LLM fails or API key is missing.
        """
        k = top_k if top_k is not None else TOP_K_RECOMMENDATIONS

        # Step 1: Filter candidates
        filter_result = self.filter_engine.apply(prefs)
        if filter_result.is_empty:
            return RecommendationResponse(
                items=[],
                summary="No restaurants match your filters. Try relaxing your budget, rating, or cuisine constraints.",
                filter_count=0,
                llm_used=False,
                messages=filter_result.messages,
            )

        candidates_df = filter_result.candidates
        num_candidates = len(candidates_df)

        # Step 2: Check API key and trigger fallback if missing
        if not get_llm_api_key():
            logger.warning("GROQ_API_KEY not found. Falling back to structured scorer ranking.")
            return self.fallback_recommend(
                candidates_df,
                k,
                "API key is missing. Set GROQ_API_KEY in your .env file to enable AI explanations."
            )

        # Step 3: Call the LLM
        try:
            # Slim candidates list down for prompt
            payload = to_llm_payload(candidates_df)
            user_prompt = build_user_prompt(prefs, payload, top_k=k)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            response_content = complete(
                messages=messages,
                response_format={"type": "json_object"},
            )

            # Step 4: Parse LLM output
            parsed_data = parse_llm_json(response_content)
            recs = parsed_data.get("recommendations", [])
            summary = parsed_data.get("summary", "")

            # Step 5: Hallucination check & name validation
            valid_recs = drop_unknown_names(recs, candidates_df)

            # Pad recommendations from scorer if LLM returned too few results
            if len(valid_recs) < k and len(valid_recs) < num_candidates:
                logger.info("LLM returned fewer valid recommendations than requested. Padding from scorer.")
                existing_names = {str(r.get("name")).strip().casefold() for r in valid_recs}
                
                # Take top candidate rows not already recommended
                padded_count = 0
                for _, row in candidates_df.iterrows():
                    row_name = str(row["name"]).strip()
                    if row_name.casefold() not in existing_names:
                        valid_recs.append({
                            "name": row_name,
                            "explanation": f"Recommended based on your preferences for rating ({row.get('rating')}), cuisines, and budget (LLM fallback explanation)."
                        })
                        existing_names.add(row_name.casefold())
                        padded_count += 1
                        if len(valid_recs) >= k or len(valid_recs) >= num_candidates:
                            break

            # Limit output list to top K
            valid_recs = valid_recs[:k]

            # Step 6: Enrich from candidates dataframe to guarantee ground truth fields
            enriched_items = enrich_from_dataframe(valid_recs, candidates_df)

            return RecommendationResponse(
                items=enriched_items,
                summary=summary,
                filter_count=num_candidates,
                llm_used=True,
                messages=[]
            )

        except Exception as exc:
            logger.error("LLM recommendation failed: %s. Falling back to structured scorer.", exc)
            return self.fallback_recommend(
                candidates_df,
                k,
                f"AI recommendation failed: {exc}. Displaying results using fallback scorer."
            )

    def fallback_recommend(self, candidates_df: pd.DataFrame, top_k: int, message: str) -> RecommendationResponse:
        """Fallback recommendation path that uses pre-LLM sorted candidates with template explanations."""
        # candidates_df is already sorted by FilterEngine using composite score and tiebreakers
        top_candidates = candidates_df.head(top_k)
        items = []

        for idx, (_, row) in enumerate(top_candidates.iterrows(), start=1):
            rating_val = row.get("rating")
            if pd.isna(rating_val):
                rating_val = None
            else:
                rating_val = float(rating_val)

            cost_val = row.get("cost_for_two")
            if pd.isna(cost_val):
                cost_val = None
            else:
                cost_val = int(cost_val)

            cuisine_val = row.get("cuisines", "")
            if pd.isna(cuisine_val):
                cuisine_val = ""

            location_val = row.get("location", "")
            if pd.isna(location_val):
                location_val = ""

            dish_liked_val = row.get("dish_liked", "")
            if pd.isna(dish_liked_val):
                dish_liked_val = ""

            book_table_val = _to_bool(row.get("book_table"))
            online_order_val = _to_bool(row.get("online_order"))

            votes_val = row.get("votes", 0)
            if pd.isna(votes_val):
                votes_val = 0
            else:
                votes_val = int(votes_val)

            items.append(
                RecommendationItem(
                    rank=idx,
                    name=str(row.get("name")),
                    cuisine=str(cuisine_val),
                    rating=rating_val,
                    estimated_cost=cost_val,
                    explanation=f"Highly rated option ({rating_val}) matching your preferences in {location_val} (LLM offline).",
                    location=str(location_val),
                    dish_liked=str(dish_liked_val),
                    book_table=book_table_val,
                    online_order=online_order_val,
                    votes=votes_val,
                )
            )

        summary = (
            "Here are the top restaurants matching your preferences, ranked using our structured scoring engine. "
            "Note: The AI recommendation engine is currently offline."
        )

        return RecommendationResponse(
            items=items,
            summary=summary,
            filter_count=len(candidates_df),
            llm_used=False,
            messages=[message]
        )

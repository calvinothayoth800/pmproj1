"""Response parser for LLM recommendation outputs."""

from __future__ import annotations

import json
import logging
import re
from typing import Any
import pandas as pd

from src.phases.phase00.output_contract import RecommendationItem

logger = logging.getLogger(__name__)

def parse_llm_json(response_text: str) -> dict[str, Any]:
    """
    Extract and parse the JSON response from the LLM.
    Handles prose wrapping or markdown code block markers.
    """
    text = response_text.strip()
    # Try searching for a JSON object block using regex
    # Looks for a block starting with { and ending with }
    json_match = re.search(r"({.*})", text, re.DOTALL)
    if json_match:
        text = json_match.group(1)

    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError("Parsed JSON is not a dictionary")
        return data
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("Failed to parse JSON from LLM response. Original response:\n%s", response_text)
        raise ValueError(f"LLM response is not valid JSON: {exc}") from exc

def drop_unknown_names(recommendations: list[dict[str, Any]], candidates_df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Filter out any recommendations whose names do not exist in the candidate list.
    Does a case-insensitive comparison.
    """
    if not recommendations or candidates_df.empty:
        return []

    candidate_names = {str(name).strip().casefold() for name in candidates_df["name"]}
    valid_recs = []

    for rec in recommendations:
        name = rec.get("name")
        if not name:
            continue
        c_name = str(name).strip().casefold()
        if c_name in candidate_names:
            valid_recs.append(rec)
        else:
            logger.warning("Dropped hallucinated restaurant name from LLM output: %s", name)

    return valid_recs

def enrich_from_dataframe(recommendations: list[dict[str, Any]], candidates_df: pd.DataFrame) -> list[RecommendationItem]:
    """
    Enrich LLM recommendations with database ground truth.
    Overwrites name casing, cuisines, rating, and cost from candidates_df.
    """
    if not recommendations or candidates_df.empty:
        return []

    # Create a lookup map: name_lower -> row (dict)
    lookup: dict[str, Any] = {}
    for _, row in candidates_df.iterrows():
        name_key = str(row["name"]).strip().casefold()
        if name_key not in lookup:
            lookup[name_key] = row

    items = []
    for idx, rec in enumerate(recommendations, start=1):
        name = rec.get("name", "")
        name_key = str(name).strip().casefold()
        row = lookup.get(name_key)

        if row is not None:
            # Overwrite fields with ground truth from the DataFrame
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

            items.append(
                RecommendationItem(
                    rank=idx,
                    name=str(row.get("name")),
                    cuisine=str(cuisine_val),
                    rating=rating_val,
                    estimated_cost=cost_val,
                    explanation=rec.get("explanation", ""),
                )
            )

    return items

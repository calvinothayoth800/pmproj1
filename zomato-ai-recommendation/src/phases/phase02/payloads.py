"""Shape filtered rows for LLM prompts (Phase 03)."""

from __future__ import annotations

from typing import Any

import pandas as pd

_LLM_COLUMNS = (
    "restaurant_id",
    "name",
    "city",
    "location",
    "cuisines",
    "rating",
    "votes",
    "cost_for_two",
    "budget_tier",
    "rest_type",
    "online_order",
    "book_table",
    "dish_liked",
    "listed_in_type",
)


def to_llm_payload(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Compact dict list with stable ``id`` (= ``restaurant_id``).

    Keeps columns useful for ranking prompts; drops nothing heavy (already excluded in Phase 01).
    """
    cols = [c for c in _LLM_COLUMNS if c in df.columns]
    slim = df[cols].copy()
    # Avoid NaN in JSON — use None
    slim = slim.where(pd.notnull(slim), None)
    rows = slim.to_dict(orient="records")
    out: list[dict[str, Any]] = []
    for r in rows:
        rid = r.get("restaurant_id")
        r["id"] = int(rid) if rid is not None else None
        out.append(r)
    return out

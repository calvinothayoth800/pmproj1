"""
Pre-LLM ranking signal (vectorized).

Higher score → stronger candidate before the model sees the shortlist.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.phases.phase00.preferences import UserPreferences


def _cuisine_hit_count(row_cuisines: str, user_cuisines: list[str]) -> int:
    if not user_cuisines:
        return 0
    tokens = [t for t in row_cuisines.casefold().split("|") if t]
    hits = 0
    for uc in user_cuisines:
        u = uc.casefold().strip()
        if not u:
            continue
        if any(u == t or u in t or t in u for t in tokens):
            hits += 1
    return hits


def composite_score(df: pd.DataFrame, prefs: UserPreferences) -> pd.Series:
    """
    Compute a sort key for each row. Not user-facing — LLM does final ranking.

    Components: rating, votes (log), cuisine overlap, budget alignment.
    """
    rating = df["rating"].fillna(0.0).astype(float)
    votes = df["votes"].clip(lower=0).astype(float)
    log_votes = np.log1p(votes)

    if prefs.has_cuisine_filter():
        cuisine_hits = df["cuisines"].map(
            lambda c, p=prefs.cuisines: _cuisine_hit_count(str(c), p)  # noqa: B008
        )
    else:
        cuisine_hits = pd.Series(0, index=df.index)

    tier = df["budget_tier"].astype(str).str.casefold()
    wanted = prefs.budget.casefold()
    budget_bonus = (tier == wanted).astype(float)
    unknown_bonus = (tier == "unknown").astype(float) * 0.25

    # Weights tuned for stable ordering (Phase 03 may ignore this ordering).
    score = (
        rating * 3.0
        + log_votes * 1.2
        + cuisine_hits.astype(float) * 2.0
        + budget_bonus * 1.5
        + unknown_bonus
    )
    return score


def tiebreak_sort_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Deterministic order when scores tie."""
    return df.sort_values(
        by=["_score", "votes", "name"],
        ascending=[False, False, True],
        kind="mergesort",
    )


"""
Structured filtering: Phase 01 dataframe → shortlist for LLM.

Imports Phase 00 ``UserPreferences`` only (no duplicate preference models).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

from src.config import MAX_CANDIDATES
from src.phases.phase00.preferences import UserPreferences
from src.phases.phase00.ui_bridge import apply_city_aliases
from src.phases.phase02.scorer import composite_score, tiebreak_sort_columns

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Outcome of applying preferences to the processed restaurant table."""

    candidates: pd.DataFrame
    funnel: dict[str, int] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.candidates) == 0


def _normalize_yes(val: Any) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    return str(val).strip().casefold() in {"yes", "y", "true", "1"}


def _mask_city(df: pd.DataFrame, prefs: UserPreferences) -> pd.Series:
    canon = apply_city_aliases(prefs.city).casefold()
    city_match = df["city"].astype(str).str.strip().str.casefold() == canon
    # Broaden with neighbourhood text (substring match — MVP).
    loc = df["location"].fillna("").astype(str).str.casefold()
    loc_match = loc.str.contains(canon, regex=False, na=False)
    return city_match | loc_match


def _mask_budget(df: pd.DataFrame, prefs: UserPreferences) -> pd.Series:
    tier = df["budget_tier"].astype(str).str.casefold()
    wanted = prefs.budget.casefold()
    # Include unknown tier so missing-cost rows are not silently excluded (see EDGE_CASES).
    return (tier == wanted) | (tier == "unknown")


def _mask_cuisine(df: pd.DataFrame, prefs: UserPreferences) -> pd.Series:
    if not prefs.has_cuisine_filter():
        return pd.Series(True, index=df.index)

    def row_match(cell: Any) -> bool:
        blob = str(cell).casefold()
        tokens = [t for t in blob.split("|") if t]
        for uc in prefs.cuisines:
            u = uc.casefold().strip()
            if not u:
                continue
            if any(u == t or u in t or t in u for t in tokens):
                return True
        return False

    return df["cuisines"].map(row_match)


def _mask_rating(df: pd.DataFrame, prefs: UserPreferences) -> pd.Series:
    if prefs.min_rating <= 0:
        return pd.Series(True, index=df.index)
    r = df["rating"]
    return r.notna() & (r >= float(prefs.min_rating))


def _mask_extras(df: pd.DataFrame, prefs: UserPreferences) -> pd.Series:
    m = pd.Series(True, index=df.index)
    ex = prefs.extras
    rt = df["rest_type"].fillna("").astype(str).str.casefold()

    if ex.family_friendly:
        fam = rt.str.contains("casual dining", regex=False) | rt.str.contains(
            "cafe", regex=False
        ) | rt.str.contains("family", regex=False)
        votes_ok = df["votes"] >= 80
        m &= fam | votes_ok

    if ex.quick_service:
        quick = rt.str.contains("quick bites", regex=False) | df["online_order"].map(_normalize_yes)
        m &= quick

    if ex.book_table:
        m &= df["book_table"].map(_normalize_yes)

    return m


def explain_empty(funnel: dict[str, int], prefs: UserPreferences) -> list[str]:
    """Human-readable reasons when the final shortlist is empty."""
    msgs: list[str] = []
    if funnel.get("start", 0) == 0:
        msgs.append("No restaurant rows loaded — build cache with scripts/build_cache.py.")
        return msgs
    if funnel.get("after_city", 0) == 0:
        msgs.append(
            f"No rows match city “{prefs.city}” (including location text). "
            "Try another spelling or broader area."
        )
    if funnel.get("after_city", 0) > 0 and funnel.get("after_rating", 0) == 0:
        msgs.append(
            f"No restaurants meet minimum rating {prefs.min_rating}. "
            "Lower the rating slider or pick a larger city."
        )
    if funnel.get("after_rating", 0) > 0 and funnel.get("after_budget", 0) == 0:
        msgs.append(
            f"No restaurants in the “{prefs.budget}” budget bucket (unknown-cost rows were allowed). "
            "Try a different budget tier."
        )
    if funnel.get("after_budget", 0) > 0 and funnel.get("after_cuisine", 0) == 0:
        msgs.append(
            "No cuisine overlap for the selected cuisines. "
            "Remove one cuisine or pick a broader type (e.g. “Chinese” vs “Sichuan”)."
        )
    if funnel.get("after_cuisine", 0) > 0 and funnel.get("after_extras", 0) == 0:
        msgs.append(
            "No rows match your service toggles (family-friendly / quick service / book table). "
            "Uncheck some options."
        )
    if not msgs:
        msgs.append("Filters eliminated all candidates — relax one constraint at a time.")
    return msgs


class FilterEngine:
    """Vectorized filters + pre-LLM scoring."""

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    def apply(
        self,
        prefs: UserPreferences,
        *,
        limit: int | None = None,
        log_steps: bool = True,
    ) -> FilterResult:
        cap = limit if limit is not None else MAX_CANDIDATES
        df = self._df
        funnel: dict[str, int] = {"start": len(df)}

        work = df
        work = work[_mask_city(work, prefs)]
        funnel["after_city"] = len(work)

        work = work[_mask_rating(work, prefs)]
        funnel["after_rating"] = len(work)

        work = work[_mask_budget(work, prefs)]
        funnel["after_budget"] = len(work)

        work = work[_mask_cuisine(work, prefs)]
        funnel["after_cuisine"] = len(work)

        work = work[_mask_extras(work, prefs)]
        funnel["after_extras"] = len(work)

        if log_steps:
            logger.info("Filter funnel %s prefs=%s", funnel, prefs.model_dump())

        if work.empty:
            return FilterResult(
                candidates=work,
                funnel=funnel,
                messages=explain_empty(funnel, prefs),
            )

        scores = composite_score(work, prefs)
        work = work.assign(_score=scores)
        work = tiebreak_sort_columns(work)
        work = work.drop(columns=["_score"], errors="ignore")
        top = work.head(cap).reset_index(drop=True)

        return FilterResult(candidates=top, funnel=funnel, messages=[])


__all__ = [
    "FilterEngine",
    "FilterResult",
    "explain_empty",
]

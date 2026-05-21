"""
Phase 01 — Normalize raw HF rows into a filter-ready schema.

Depends on Phase 00 only for ``apply_city_aliases`` (shared UI/data city naming).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import pandas as pd

from src.phases.phase00.ui_bridge import apply_city_aliases

logger = logging.getLogger(__name__)

COL_COST = "approx_cost(for two people)"
COL_LISTED_CITY = "listed_in(city)"
COL_LISTED_TYPE = "listed_in(type)"

# Minimum bucket size to use city-specific cost quantiles (else fall back to global).
_MIN_PER_CITY_FOR_QUANTILES = 30


def parse_rate(val: Any) -> Optional[float]:
    """Parse dataset ``rate`` into 0–5 float; unusable tokens become None."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip().upper()
    if not s or s in {"-", "NAN", "NONE"}:
        return None
    if s == "NEW":
        return None
    if "/" in s:
        s = s.split("/", 1)[0].strip()
    try:
        x = float(s)
    except ValueError:
        return None
    if x < 0 or x > 5:
        return None
    return x


def parse_cost(val: Any) -> Optional[int]:
    """
    Parse ``approx_cost(for two people)`` into INR integer.
    Handles commas, currency noise, and simple ranges (uses midpoint).
    """
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    if not s or s.upper() in {"NAN", "NONE", "-"}:
        return None
    chunks = re.split(r"[-–—]+", s)
    numbers: list[int] = []
    for ch in chunks:
        digits = re.sub(r"\D+", "", ch)
        if digits:
            try:
                numbers.append(int(digits))
            except ValueError:
                continue
    if not numbers:
        return None
    if len(numbers) >= 2:
        return int(round((numbers[0] + numbers[1]) / 2))
    return numbers[0]


def normalize_cuisines_cell(val: Any) -> str:
    """Lowercase pipe-separated cuisines for matching."""
    if val is None or pd.isna(val):
        return ""
    parts = [p.strip().lower() for p in str(val).split(",")]
    parts = [p for p in parts if p]
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return "|".join(out)


def canonical_city(raw: Any) -> str:
    """Normalize listing city using shared UI aliases where applicable."""
    if raw is None or pd.isna(raw):
        return ""
    return apply_city_aliases(str(raw).strip())


def _tier_labels(costs: pd.Series) -> tuple[float, float]:
    """Return (q33, q66) cost breakpoints for low/medium/high."""
    valid = costs.dropna()
    if valid.empty:
        return (500.0, 1000.0)
    q33 = float(valid.quantile(1 / 3))
    q66 = float(valid.quantile(2 / 3))
    if q33 >= q66:
        q66 = q33 + 1.0
    return q33, q66


def assign_budget_tiers(df: pd.DataFrame) -> pd.Series:
    """
    Assign ``low`` / ``medium`` / ``high`` using per-city quantiles when enough samples,
    otherwise global quantiles on valid ``cost_for_two``.
    """
    costs = df["cost_for_two"]
    global_q33, global_q66 = _tier_labels(costs)

    q33_series = pd.Series(global_q33, index=df.index, dtype=float)
    q66_series = pd.Series(global_q66, index=df.index, dtype=float)

    if "city" in df.columns:
        for city, grp in df.groupby("city"):
            if not city:
                continue
            sub = grp["cost_for_two"]
            if sub.notna().sum() >= _MIN_PER_CITY_FOR_QUANTILES:
                cq33, cq66 = _tier_labels(sub)
                q33_series.loc[grp.index] = cq33
                q66_series.loc[grp.index] = cq66

    tiers = pd.Series("unknown", index=df.index, dtype=object)
    mask = costs.notna()
    tiers.loc[mask & (costs <= q33_series)] = "low"
    tiers.loc[mask & (costs > q33_series) & (costs <= q66_series)] = "medium"
    tiers.loc[mask & (costs > q66_series)] = "high"
    return tiers


def preprocess(df: pd.DataFrame, *, dedupe: bool = True) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Select columns, parse numeric fields, normalize text, assign tiers.

    Returns:
        Processed dataframe and diagnostics counters (invalid_rate, etc.).
    """
    diagnostics: dict[str, int] = {}

    needed = [
        "name",
        "location",
        "rest_type",
        "online_order",
        "book_table",
        "rate",
        "votes",
        "cuisines",
        COL_COST,
        "dish_liked",
        COL_LISTED_CITY,
        COL_LISTED_TYPE,
        "address",
    ]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing expected columns: {missing}")

    out = pd.DataFrame()
    out["name"] = df["name"].astype(str).str.strip()
    out["location"] = df["location"].fillna("").astype(str).str.strip()
    out["city"] = df[COL_LISTED_CITY].map(canonical_city).fillna("").astype(str).str.strip()
    out["listed_in_type"] = df[COL_LISTED_TYPE].fillna("").astype(str).str.strip()
    out["rest_type"] = df["rest_type"].fillna("").astype(str).str.strip()
    out["online_order"] = df["online_order"].fillna("").astype(str).str.strip()
    out["book_table"] = df["book_table"].fillna("").astype(str).str.strip()
    out["dish_liked"] = df["dish_liked"].fillna("").astype(str).str.strip()

    raw_rates = df["rate"]
    parsed_rates = raw_rates.map(parse_rate)
    diagnostics["invalid_rate"] = int((raw_rates.notna() & parsed_rates.isna()).sum())
    out["rating"] = parsed_rates

    votes = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)
    out["votes"] = votes

    raw_cost = df[COL_COST]
    parsed_cost = raw_cost.map(parse_cost)
    raw_nonempty = raw_cost.notna() & (raw_cost.astype(str).str.strip() != "")
    diagnostics["invalid_cost"] = int((raw_nonempty & parsed_cost.isna()).sum())
    out["cost_for_two"] = parsed_cost

    out["cuisines"] = df["cuisines"].map(normalize_cuisines_cell)

    if dedupe:
        addr = df["address"].fillna("").astype(str).str.strip()
        before = len(out)
        work = out.assign(_addr=addr)
        work = work.sort_values(by="votes", ascending=False)
        work = work.drop_duplicates(subset=["name", "_addr"], keep="first")
        work = work.drop(columns=["_addr"])
        diagnostics["deduped_rows"] = before - len(work)
        out = work.reset_index(drop=True)
    else:
        diagnostics["deduped_rows"] = 0
        out = out.reset_index(drop=True)

    out["budget_tier"] = assign_budget_tiers(out)
    out.insert(0, "restaurant_id", range(len(out)))

    keep_cols = [
        "restaurant_id",
        "name",
        "city",
        "location",
        "cuisines",
        "rating",
        "votes",
        "cost_for_two",
        "budget_tier",
        "listed_in_type",
        "rest_type",
        "online_order",
        "book_table",
        "dish_liked",
    ]
    out = out[keep_cols]

    logger.info(
        "Preprocessed rows=%s invalid_rate_cells~%s invalid_cost_cells~=%s deduped=%s",
        len(out),
        diagnostics.get("invalid_rate", 0),
        diagnostics.get("invalid_cost", 0),
        diagnostics.get("deduped_rows", 0),
    )
    return out, diagnostics

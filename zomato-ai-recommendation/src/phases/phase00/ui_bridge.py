"""
Bridge between raw web UI values (Streamlit widgets, JSON body) and ``UserPreferences``.

Keeps normalization and caps in one place so Phase 04 forms stay thin.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from src.phases.phase00.preferences import BudgetTier, PreferenceExtras, UserPreferences

# Limits aligned with docs/EDGE_CASES.md (avoid over-filtering).
MAX_UI_CUISINES: int = 10

# Common UI spellings → dataset-facing token (extend in Phase 01 DATA_NOTES).
_CITY_ALIASES: dict[str, str] = {
    "bengaluru": "Bangalore",
    "blr": "Bangalore",
    "gurugram": "Gurgaon",
    "noida": "Noida",
    "new delhi": "Delhi",
    "ncr": "Delhi",
}


def apply_city_aliases(city: str) -> str:
    """Normalize user-entered city using a small alias map (case-insensitive)."""
    key = city.strip().casefold()
    return _CITY_ALIASES.get(key, city.strip())


def _coerce_budget(raw: Any) -> BudgetTier:
    if raw is None:
        raise ValueError("budget is required")
    s = str(raw).strip().casefold()
    if s not in ("low", "medium", "high"):
        raise ValueError("budget must be one of: low, medium, high")
    return s  # type: ignore[return-value]


def _coerce_extras(raw: Any) -> PreferenceExtras:
    if raw is None:
        return PreferenceExtras()
    if isinstance(raw, PreferenceExtras):
        return raw
    if not isinstance(raw, dict):
        raise TypeError("extras must be a dict or PreferenceExtras")
    return PreferenceExtras(
        family_friendly=bool(raw.get("family_friendly", False)),
        quick_service=bool(raw.get("quick_service", False)),
        book_table=bool(raw.get("book_table", False)),
    )


def preferences_from_ui(payload: dict[str, Any]) -> UserPreferences:
    """
    Build ``UserPreferences`` from a dict (e.g. Streamlit ``st.session_state`` or FastAPI JSON).

    Expected keys:
        city (str), budget (str), cuisines (list[str] | str), min_rating (float),
        extras (dict, optional)

    Raises:
        ValidationError: invalid or out-of-range fields
        ValueError: semantic errors (e.g. unknown budget)
    """
    city = apply_city_aliases(str(payload.get("city", "")))
    budget = _coerce_budget(payload.get("budget"))

    raw_rating = payload.get("min_rating", 0.0)
    try:
        min_rating = float(raw_rating)
    except (TypeError, ValueError) as e:
        raise ValueError("min_rating must be a number") from e

    extras = _coerce_extras(payload.get("extras"))

    prefs = UserPreferences(
        city=city,
        budget=budget,
        cuisines=payload.get("cuisines") or [],
        min_rating=min_rating,
        extras=extras,
    )
    if len(prefs.cuisines) > MAX_UI_CUISINES:
        return prefs.model_copy(update={"cuisines": prefs.cuisines[:MAX_UI_CUISINES]})
    return prefs


def preferences_from_ui_safe(payload: dict[str, Any]) -> tuple[UserPreferences | None, list[str]]:
    """
    Same as ``preferences_from_ui`` but returns validation errors as strings for UI display.
    """
    try:
        return preferences_from_ui(payload), []
    except ValidationError as e:
        msgs = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return None, msgs
    except (ValueError, TypeError) as e:
        return None, [str(e)]

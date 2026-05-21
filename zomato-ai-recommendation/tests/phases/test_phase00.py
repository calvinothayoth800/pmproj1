"""Tests for Phase 00 — web UI contract."""

import pytest
from pydantic import ValidationError

from src.phases.phase00 import (
    UserPreferences,
    apply_city_aliases,
    preferences_from_ui,
    preferences_from_ui_safe,
)
from src.phases.phase00.output_contract import RecommendationResponse


def test_user_preferences_dedupes_cuisines_case_insensitive() -> None:
    p = UserPreferences(
        city="Delhi",
        budget="medium",
        cuisines=["Chinese", "chinese", " North Indian "],
        min_rating=3.5,
    )
    assert p.cuisines == ["Chinese", "North Indian"]


def test_preferences_from_ui_city_alias() -> None:
    p = preferences_from_ui(
        {
            "city": "Bengaluru",
            "budget": "low",
            "cuisines": ["Italian"],
            "min_rating": 4.0,
        }
    )
    assert p.city == "Bangalore"


def test_preferences_from_ui_cuisine_string_split() -> None:
    p = preferences_from_ui(
        {
            "city": "Delhi",
            "budget": "high",
            "cuisines": "Chinese, Thai, ",
            "min_rating": 0,
        }
    )
    assert p.cuisines == ["Chinese", "Thai"]


def test_preferences_from_ui_truncates_cuisines() -> None:
    many = [f"c{i}" for i in range(15)]
    p = preferences_from_ui(
        {"city": "Delhi", "budget": "low", "cuisines": many, "min_rating": 0}
    )
    assert len(p.cuisines) == 10


def test_preferences_from_ui_invalid_budget() -> None:
    with pytest.raises(ValueError, match="budget"):
        preferences_from_ui(
            {"city": "Delhi", "budget": "luxury", "cuisines": [], "min_rating": 0}
        )


def test_preferences_from_ui_safe_returns_errors() -> None:
    prefs, errs = preferences_from_ui_safe(
        {"city": "", "budget": "low", "cuisines": [], "min_rating": 0}
    )
    assert prefs is None
    assert errs


def test_apply_city_aliases_unknown_unchanged() -> None:
    assert apply_city_aliases("  Pune  ") == "Pune"


def test_min_rating_validation() -> None:
    with pytest.raises(ValidationError):
        UserPreferences(city="Delhi", budget="low", cuisines=[], min_rating=5.5)


def test_placeholder_response() -> None:
    r = RecommendationResponse.not_implemented_placeholder()
    assert r.items == []
    assert r.messages and "Phase" in r.messages[0]

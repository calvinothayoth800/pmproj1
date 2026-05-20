"""Tests for Phase 02 filtering engine."""

from __future__ import annotations

import time

import pandas as pd

from src.phases.phase00.preferences import PreferenceExtras, UserPreferences
from src.phases.phase02 import FilterEngine, explain_empty, to_llm_payload
from src.phases.phase02.scorer import composite_score


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "restaurant_id": 1,
                "name": "A",
                "city": "Bangalore",
                "location": "Koramangala",
                "cuisines": "chinese|thai",
                "rating": 4.2,
                "votes": 120,
                "cost_for_two": 800,
                "budget_tier": "medium",
                "listed_in_type": "",
                "rest_type": "Casual Dining",
                "online_order": "Yes",
                "book_table": "Yes",
                "dish_liked": "",
            },
            {
                "restaurant_id": 2,
                "name": "B",
                "city": "Bangalore",
                "location": "Indiranagar",
                "cuisines": "north indian",
                "rating": 3.8,
                "votes": 40,
                "cost_for_two": 400,
                "budget_tier": "low",
                "listed_in_type": "",
                "rest_type": "Quick Bites",
                "online_order": "Yes",
                "book_table": "No",
                "dish_liked": "",
            },
            {
                "restaurant_id": 3,
                "name": "C",
                "city": "Delhi",
                "location": "CP",
                "cuisines": "italian",
                "rating": 4.8,
                "votes": 300,
                "cost_for_two": 2000,
                "budget_tier": "high",
                "listed_in_type": "",
                "rest_type": "Fine Dining",
                "online_order": "No",
                "book_table": "Yes",
                "dish_liked": "",
            },
            {
                "restaurant_id": 4,
                "name": "D",
                "city": "Bangalore",
                "location": "Sector 1",
                "cuisines": "",
                "rating": None,
                "votes": 10,
                "cost_for_two": None,
                "budget_tier": "unknown",
                "listed_in_type": "",
                "rest_type": "Unknown",
                "online_order": "No",
                "book_table": "No",
                "dish_liked": "",
            },
        ]
    )


def test_city_and_cuisine_filter() -> None:
    prefs = UserPreferences(
        city="Bangalore",
        budget="medium",
        cuisines=["Chinese"],
        min_rating=4.0,
    )
    eng = FilterEngine(_sample_df())
    out = eng.apply(prefs, limit=10)
    assert not out.is_empty
    assert len(out.candidates) == 1
    assert out.candidates.iloc[0]["name"] == "A"


def test_min_rating_excludes_null_rating_when_positive() -> None:
    prefs = UserPreferences(city="Bangalore", budget="low", cuisines=[], min_rating=4.0)
    eng = FilterEngine(_sample_df())
    out = eng.apply(prefs, limit=10)
    names = set(out.candidates["name"])
    assert "D" not in names


def test_budget_accepts_unknown_tier_rows() -> None:
    prefs = UserPreferences(city="Bangalore", budget="high", cuisines=[], min_rating=0.0)
    eng = FilterEngine(_sample_df())
    out = eng.apply(prefs, limit=10)
    assert "D" in set(out.candidates["name"])


def test_book_table_extra() -> None:
    prefs = UserPreferences(
        city="Bangalore",
        budget="medium",
        cuisines=[],
        min_rating=0.0,
        extras=PreferenceExtras(book_table=True),
    )
    eng = FilterEngine(_sample_df())
    out = eng.apply(prefs, limit=10)
    names = set(out.candidates["name"])
    assert names <= {"A"}


def test_empty_city_messages() -> None:
    prefs = UserPreferences(city="Pune", budget="low", cuisines=[], min_rating=0.0)
    eng = FilterEngine(_sample_df())
    out = eng.apply(prefs, limit=10)
    assert out.is_empty
    assert out.messages
    assert any("city" in m.casefold() for m in out.messages)


def test_explain_empty_rating_branch() -> None:
    funnel = {
        "start": 10,
        "after_city": 5,
        "after_rating": 0,
        "after_budget": 0,
        "after_cuisine": 0,
        "after_extras": 0,
    }
    prefs = UserPreferences(city="X", budget="low", cuisines=[], min_rating=4.5)
    msgs = explain_empty(funnel, prefs)
    assert any("rating" in m.casefold() for m in msgs)


def test_to_llm_payload_stable_ids() -> None:
    prefs = UserPreferences(city="Bangalore", budget="medium", cuisines=[], min_rating=0.0)
    eng = FilterEngine(_sample_df())
    out = eng.apply(prefs, limit=2)
    payload = to_llm_payload(out.candidates)
    assert len(payload) <= 2
    assert all("id" in row and row["name"] for row in payload)


def test_composite_score_series_aligned() -> None:
    df = _sample_df().iloc[:2]
    prefs = UserPreferences(city="Bangalore", budget="medium", cuisines=["Chinese"], min_rating=0.0)
    s = composite_score(df, prefs)
    assert len(s) == 2


def test_filter_performance_bulk_rows() -> None:
    """Warm-cache-style throughput on ~8k synthetic rows (target << 200ms)."""
    base = _sample_df()
    frames = []
    for i in range(500):
        chunk = base.copy()
        chunk["restaurant_id"] = chunk["restaurant_id"] + i * 10
        chunk["name"] = chunk["name"] + f"_{i}"
        frames.append(chunk)
    big = pd.concat(frames, ignore_index=True)
    prefs = UserPreferences(city="Bangalore", budget="medium", cuisines=["indian"], min_rating=3.5)
    eng = FilterEngine(big)
    t0 = time.perf_counter()
    result = eng.apply(prefs, limit=35, log_steps=False)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.25, f"filter took {elapsed:.3f}s"
    assert len(result.candidates) <= 35


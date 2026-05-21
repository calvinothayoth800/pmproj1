"""Tests for preprocessor parsers and preprocess pipeline."""

from __future__ import annotations

import pandas as pd
import pytest
from typing import Optional

from src.phases.phase01.preprocessor import (
    COL_COST,
    COL_LISTED_CITY,
    COL_LISTED_TYPE,
    normalize_cuisines_cell,
    parse_cost,
    parse_rate,
    preprocess,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4.1/5", 4.1),
        ("4.5", 4.5),
        ("NEW", None),
        ("-", None),
        ("", None),
        (None, None),
        ("6.0", None),
        ("-1", None),
    ],
)
def test_parse_rate(raw: object, expected: Optional[float]) -> None:
    got = parse_rate(raw)
    if expected is None:
        assert got is None
    else:
        assert got == pytest.approx(expected)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("300", 300),
        ("1,200", 1200),
        ("₹800", 800),
        ("500-1,000", 750),
        ("-", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_cost(raw: object, expected: Optional[int]) -> None:
    assert parse_cost(raw) == expected


def test_normalize_cuisines_cell() -> None:
    assert normalize_cuisines_cell("Chinese, Thai , chinese") == "chinese|thai"


def _minimal_raw_df(n: int = 3) -> pd.DataFrame:
    rows = []
    for i in range(n):
        rows.append(
            {
                "name": f"Place {i}",
                "location": f"Area{i}",
                "rest_type": "Casual Dining",
                "online_order": "Yes",
                "book_table": "No",
                "rate": "4.2/5",
                "votes": 100 + i,
                "cuisines": "Chinese, Thai",
                COL_COST: "800",
                "dish_liked": "",
                COL_LISTED_CITY: "Bangalore",
                COL_LISTED_TYPE: "Delivery",
                "address": f"{i} Main Rd",
            }
        )
    return pd.DataFrame(rows)


def test_preprocess_pipeline_basic() -> None:
    df = _minimal_raw_df()
    out, diag = preprocess(df, dedupe=False)
    assert len(out) == 3
    assert list(out.columns[0:5]) == ["restaurant_id", "name", "city", "location", "cuisines"]
    assert out.loc[0, "rating"] == pytest.approx(4.2)
    assert out.loc[0, "cost_for_two"] == 800
    assert out.loc[0, "cuisines"] == "chinese|thai"
    assert out.loc[0, "budget_tier"] in {"low", "medium", "high", "unknown"}
    assert diag["deduped_rows"] == 0


def test_preprocess_dedupes_by_name_address() -> None:
    df = _minimal_raw_df(2)
    df.loc[1, "name"] = "Place 0"
    df.loc[1, "address"] = "0 Main Rd"
    out, diag = preprocess(df, dedupe=True)
    assert len(out) == 1
    assert diag["deduped_rows"] == 1

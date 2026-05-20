"""RestaurantRecord validates a processed dataframe row."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.phases.phase01.restaurant_record import RestaurantRecord


def _row_to_record(row: pd.Series) -> RestaurantRecord:
    d = row.to_dict()
    if isinstance(d.get("rating"), float) and math.isnan(d["rating"]):
        d["rating"] = None
    if isinstance(d.get("cost_for_two"), float) and math.isnan(d["cost_for_two"]):
        d["cost_for_two"] = None
    return RestaurantRecord.model_validate(d)


def test_restaurant_record_from_processed_row() -> None:
    row = pd.Series(
        {
            "restaurant_id": 0,
            "name": "Test",
            "city": "Delhi",
            "location": "CP",
            "cuisines": "north indian|chinese",
            "rating": 4.2,
            "votes": 50,
            "cost_for_two": 900,
            "budget_tier": "medium",
            "listed_in_type": "Delivery",
            "rest_type": "Casual Dining",
            "online_order": "Yes",
            "book_table": "No",
            "dish_liked": "",
        }
    )
    rec = _row_to_record(row)
    assert rec.cuisine_list() == ["north indian", "chinese"]

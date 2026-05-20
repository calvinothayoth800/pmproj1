"""Parquet cache roundtrip (no Hugging Face)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.phases.phase01.cache import CACHE_VERSION, load_processed, save_processed


def test_save_load_roundtrip(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "restaurant_id": [0, 1],
            "name": ["A", "B"],
            "city": ["Delhi", "Delhi"],
            "location": ["x", "y"],
            "cuisines": ["north indian", "chinese"],
            "rating": [4.0, 3.5],
            "votes": [10, 5],
            "cost_for_two": [500, 1200],
            "budget_tier": ["low", "high"],
            "listed_in_type": ["", ""],
            "rest_type": ["", ""],
            "online_order": ["Yes", "No"],
            "book_table": ["No", "No"],
            "dish_liked": ["", ""],
        }
    )
    path = tmp_path / "restaurants.parquet"
    save_processed(df, path, extra_meta={"test": True})
    loaded = load_processed(path)
    assert len(loaded) == 2
    assert list(loaded.columns) == list(df.columns)
    meta_path = path.with_name(path.name + ".meta.json")
    assert meta_path.is_file()
    assert CACHE_VERSION in meta_path.read_text(encoding="utf-8")

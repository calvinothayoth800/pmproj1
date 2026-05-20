#!/usr/bin/env python3
"""CLI smoke test for Phase 02 filtering (loads Phase 01 Parquet cache)."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_CACHE_PATH, PROJECT_ROOT  # noqa: E402
from src.phases.phase00.preferences import PreferenceExtras, UserPreferences  # noqa: E402
from src.phases.phase01 import load_processed  # noqa: E402
from src.phases.phase02 import FilterEngine, to_llm_payload  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter restaurants (Phase 02 smoke test).")
    parser.add_argument("--city", required=True)
    parser.add_argument("--budget", choices=("low", "medium", "high"), required=True)
    parser.add_argument("--cuisines", default="", help="Comma-separated")
    parser.add_argument("--min-rating", type=float, default=0.0)
    parser.add_argument("--family", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--book", action="store_true")
    parser.add_argument(
        "--cache",
        type=Path,
        default=DATA_CACHE_PATH,
        help=f"Parquet path (default: {DATA_CACHE_PATH})",
    )
    parser.add_argument("--json", action="store_true", help="Print LLM payload JSON")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    path = args.cache
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    df = load_processed(path)

    cuisines = [c.strip() for c in args.cuisines.split(",") if c.strip()]
    prefs = UserPreferences(
        city=args.city,
        budget=args.budget,  # type: ignore[arg-type]
        cuisines=cuisines,
        min_rating=args.min_rating,
        extras=PreferenceExtras(
            family_friendly=args.family,
            quick_service=args.quick,
            book_table=args.book,
        ),
    )

    engine = FilterEngine(df)
    result = engine.apply(prefs, limit=args.limit)
    print("funnel:", json.dumps(result.funnel, indent=2))
    if result.messages:
        print("messages:", *result.messages, sep="\n  - ")
    print("candidates:", len(result.candidates))
    if args.json and not result.candidates.empty:
        print(json.dumps(to_llm_payload(result.candidates), indent=2)[:4000])
    elif not result.candidates.empty:
        cols = ["name", "city", "rating", "cost_for_two", "budget_tier", "cuisines"]
        print(result.candidates[cols].head(10).to_string(index=False))

    return 0 if not result.is_empty else 1


if __name__ == "__main__":
    raise SystemExit(main())

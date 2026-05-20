#!/usr/bin/env python3
"""CLI smoke test for Phase 03 recommendation (loads Phase 01 Parquet cache, calls Groq LLM)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_CACHE_PATH, PROJECT_ROOT
from src.phases.phase00.preferences import PreferenceExtras, UserPreferences
from src.phases.phase01 import load_processed
from src.services.recommendation_service import RecommendationService


def main() -> int:
    parser = argparse.ArgumentParser(description="Recommend restaurants (Phase 03 smoke test).")
    parser.add_argument("--city", required=True)
    parser.add_argument("--budget", choices=("low", "medium", "high"), required=True)
    parser.add_argument("--cuisines", default="", help="Comma-separated cuisines")
    parser.add_argument("--min-rating", type=float, default=0.0)
    parser.add_argument("--family", action="store_true")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--book", action="store_true")
    parser.add_argument("--notes", default=None, help="Additional text preferences / notes")
    parser.add_argument(
        "--cache",
        type=Path,
        default=DATA_CACHE_PATH,
        help=f"Parquet path (default: {DATA_CACHE_PATH})",
    )
    parser.add_argument("--limit", type=int, default=5, help="Number of recommendations to fetch")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    path = args.cache
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    
    print(f"Loading cache from {path}...")
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
        additional_notes=args.notes,
    )

    print("Initializing RecommendationService...")
    service = RecommendationService(df)
    
    print(f"Fetching top {args.limit} recommendations...")
    response = service.recommend(prefs, top_k=args.limit)

    print("\n" + "=" * 80)
    print("RECOMMENDATION RESPONSE")
    print("=" * 80)
    print(f"Filtered Candidates: {response.filter_count}")
    print(f"LLM Used: {response.llm_used}")
    if response.messages:
        print(f"Messages: {response.messages}")
    
    print("\nSummary:")
    print(response.summary or "No summary provided.")

    print("\nRecommendations:")
    if not response.items:
        print("  No recommendations returned.")
    else:
        for item in response.items:
            print(f"\n{item.rank}. {item.name} | Rating: {item.rating or 'N/A'} | Cost for two: INR {item.estimated_cost or 'N/A'}")
            print(f"   Cuisines: {item.cuisine}")
            print(f"   AI Explanation: {item.explanation}")
    print("=" * 80)

    return 0 if response.items else 1


if __name__ == "__main__":
    raise SystemExit(main())

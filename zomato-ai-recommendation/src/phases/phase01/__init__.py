"""
Phase 01 — Data foundation (canonical implementation).

All ingest / preprocess / cache code lives **here** so tracebacks read
``src.phases.phase01.*`` and git rollbacks can target this package.

Compatibility imports for older paths: ``src.data`` (thin facade).
"""

from src.phases.phase01.cache import CACHE_VERSION, load_processed, save_processed
from src.phases.phase01.loader import HF_DATASET_NAME, load_raw
from src.phases.phase01.meta import DEPENDS_ON_PHASE_IDS, PHASE_ID, PHASE_SLUG
from src.phases.phase01.preprocessor import (
    COL_COST,
    COL_LISTED_CITY,
    COL_LISTED_TYPE,
    assign_budget_tiers,
    canonical_city,
    normalize_cuisines_cell,
    parse_cost,
    parse_rate,
    preprocess,
)
from src.phases.phase01.restaurant_record import RestaurantRecord

__all__ = [
    "CACHE_VERSION",
    "COL_COST",
    "COL_LISTED_CITY",
    "COL_LISTED_TYPE",
    "DEPENDS_ON_PHASE_IDS",
    "HF_DATASET_NAME",
    "PHASE_ID",
    "PHASE_SLUG",
    "RestaurantRecord",
    "assign_budget_tiers",
    "canonical_city",
    "load_processed",
    "load_raw",
    "normalize_cuisines_cell",
    "parse_cost",
    "parse_rate",
    "preprocess",
    "save_processed",
]

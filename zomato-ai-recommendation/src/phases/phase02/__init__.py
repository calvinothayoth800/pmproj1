"""
Phase 02 — Structured filtering + pre-LLM scoring.

Depends on Phase 00 (``UserPreferences``) and Phase 01 (processed dataframe schema).
"""

from src.phases.phase02.engine import FilterEngine, FilterResult, explain_empty
from src.phases.phase02.meta import DEPENDS_ON_PHASE_IDS, PHASE_ID, PHASE_SLUG
from src.phases.phase02.payloads import to_llm_payload
from src.phases.phase02.scorer import composite_score

__all__ = [
    "DEPENDS_ON_PHASE_IDS",
    "PHASE_ID",
    "PHASE_SLUG",
    "FilterEngine",
    "FilterResult",
    "composite_score",
    "explain_empty",
    "to_llm_payload",
]

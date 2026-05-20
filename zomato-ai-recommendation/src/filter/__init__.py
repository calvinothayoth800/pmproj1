"""Compatibility facade — canonical filtering lives in ``src.phases.phase02``."""

from src.phases.phase02 import (
    FilterEngine,
    FilterResult,
    composite_score,
    explain_empty,
    to_llm_payload,
)

__all__ = [
    "FilterEngine",
    "FilterResult",
    "composite_score",
    "explain_empty",
    "to_llm_payload",
]

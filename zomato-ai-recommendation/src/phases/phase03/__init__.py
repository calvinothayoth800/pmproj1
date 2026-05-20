"""Phase 03 — LLM recommendation.

Re-exports the core LLM prompts, client, parser, and service orchestrator.
"""

from src.phases.phase03.meta import DEPENDS_ON_PHASE_IDS, PHASE_ID, PHASE_SLUG
from src.models.recommendation import RestaurantRecommendation, RecommendationItem, RecommendationResponse
from src.llm.client import complete
from src.llm.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.llm.parser import parse_llm_json, enrich_from_dataframe, drop_unknown_names
from src.services.recommendation_service import RecommendationService

__all__ = [
    "DEPENDS_ON_PHASE_IDS",
    "PHASE_ID",
    "PHASE_SLUG",
    "RestaurantRecommendation",
    "RecommendationItem",
    "RecommendationResponse",
    "complete",
    "SYSTEM_PROMPT",
    "build_user_prompt",
    "parse_llm_json",
    "enrich_from_dataframe",
    "drop_unknown_names",
    "RecommendationService",
]

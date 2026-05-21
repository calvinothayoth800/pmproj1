"""
Phase 00 — Web UI contract layer.

Defines validated input from the future Streamlit UI and stable output shapes
the UI can render before filtering / LLM exist.

Rollback: remove this folder and stop importing ``src.phases.phase00`` from
later phases; UI forms must then be updated if they depended on these types.
"""

from src.phases.phase00.meta import DEPENDS_ON_PHASE_IDS, PHASE_ID, PHASE_SLUG
from src.phases.phase00.output_contract import (
    RecommendationItem,
    RecommendationResponse,
)
from src.phases.phase00.preferences import (
    BudgetTier,
    PreferenceExtras,
    UserPreferences,
)
from src.phases.phase00.ui_bridge import (
    MAX_UI_CUISINES,
    apply_city_aliases,
    preferences_from_ui,
    preferences_from_ui_safe,
)

__all__ = [
    "BudgetTier",
    "DEPENDS_ON_PHASE_IDS",
    "MAX_UI_CUISINES",
    "PHASE_ID",
    "PHASE_SLUG",
    "PreferenceExtras",
    "RecommendationItem",
    "RecommendationResponse",
    "UserPreferences",
    "apply_city_aliases",
    "preferences_from_ui",
    "preferences_from_ui_safe",
]

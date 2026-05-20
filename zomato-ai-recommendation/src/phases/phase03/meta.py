"""Phase identity — keep aligned with ``src.phases.registry``."""

PHASE_ID = "03"
PHASE_SLUG = "llm_recommendation"
DEPENDS_ON_PHASE_IDS: tuple[str, ...] = ("02",)

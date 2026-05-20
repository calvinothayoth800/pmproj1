"""Phase identity — keep aligned with ``src.phases.registry``."""

PHASE_ID = "02"
PHASE_SLUG = "filtering_engine"
DEPENDS_ON_PHASE_IDS: tuple[str, ...] = ("01",)

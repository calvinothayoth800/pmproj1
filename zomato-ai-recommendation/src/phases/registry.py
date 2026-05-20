"""
Explicit phased architecture — dependency order and rollback hints.

Use this when explaining scope to engineers or when bisecting production-like issues:
each phase is an intentional boundary you can revert in isolation *if* downstream
phases only import from earlier phases (see ``DEPENDS_ON``).

This module intentionally avoids importing phase packages (no import cycles).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhaseManifest:
    """One delivered slice of the product; maps to ``src.phases.phaseNN``."""

    id: str
    slug: str
    package: str
    depends_on: tuple[str, ...]
    rollback_hint: str


# Ordered roughly by delivery (also respects depends_on).
PHASE_MANIFESTS: tuple[PhaseManifest, ...] = (
    PhaseManifest(
        id="00",
        slug="web_contract",
        package="src.phases.phase00",
        depends_on=(),
        rollback_hint=(
            "Delete ``src/phases/phase00``. Downstream must stop importing "
            "UserPreferences / RecommendationResponse or replace contracts."
        ),
    ),
    PhaseManifest(
        id="01",
        slug="data_foundation",
        package="src.phases.phase01",
        depends_on=("00",),
        rollback_hint=(
            "Delete ``src/phases/phase01``, drop ``scripts/build_cache.py`` usage, "
            "remove ``src.data`` facade. Phase 02+ cannot load Parquet until restored."
        ),
    ),
    PhaseManifest(
        id="02",
        slug="filtering_engine",
        package="src.phases.phase02",
        depends_on=("01",),
        rollback_hint=(
            "Delete ``src/phases/phase02``. Remove ``scripts/try_filter.py`` references; "
            "Phase 03 must not assume FilterEngine output shape."
        ),
    ),
)


def phase_ids_in_order() -> tuple[str, ...]:
    return tuple(p.id for p in PHASE_MANIFESTS)


def assert_dependency_order() -> None:
    """Lightweight sanity check (invoke from tests). Earlier phases must not depend on later ones."""
    known = {p.id for p in PHASE_MANIFESTS}
    for p in PHASE_MANIFESTS:
        for dep in p.depends_on:
            assert dep in known, f"Phase {p.id} depends on unknown {dep}"
            dep_order = phase_ids_in_order().index(dep)
            self_order = phase_ids_in_order().index(p.id)
            assert dep_order < self_order, f"Phase {p.id} must depend only on earlier phases, got {dep}"

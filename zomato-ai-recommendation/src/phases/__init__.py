"""
Phased delivery layout.

- ``registry``: machine-readable phase order + rollback hints (PM/engineering artifact).
- ``phase00``, ``phase01``, …: implementations (import only from earlier phases).
"""

from src.phases.registry import PHASE_MANIFESTS, PhaseManifest, assert_dependency_order, phase_ids_in_order

__all__ = [
    "PHASE_MANIFESTS",
    "PhaseManifest",
    "assert_dependency_order",
    "phase_ids_in_order",
]

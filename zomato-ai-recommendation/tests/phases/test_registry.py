"""Phase registry invariants — documents modular boundaries in executable form."""

from src.phases.registry import PHASE_MANIFESTS, assert_dependency_order, phase_ids_in_order


def test_phase_order_matches_manifest_sequence() -> None:
    assert phase_ids_in_order() == tuple(p.id for p in PHASE_MANIFESTS)


def test_dependency_order_valid() -> None:
    assert_dependency_order()


def test_manifests_have_unique_ids() -> None:
    ids = [p.id for p in PHASE_MANIFESTS]
    assert len(ids) == len(set(ids))

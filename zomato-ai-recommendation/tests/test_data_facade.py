"""``src.data`` is a backward-compat facade over Phase 01."""

from src.data import CACHE_VERSION, load_raw
from src.phases.phase01 import CACHE_VERSION as CANONICAL_CACHE_VERSION
from src.phases.phase01 import load_raw as canonical_load_raw


def test_data_facade_delegates_to_phase01() -> None:
    assert load_raw is canonical_load_raw
    assert CACHE_VERSION == CANONICAL_CACHE_VERSION

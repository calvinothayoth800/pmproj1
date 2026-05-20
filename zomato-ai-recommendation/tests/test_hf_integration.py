"""Optional Hugging Face download test (network + large artifact)."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_HF_INTEGRATION") != "1",
    reason="Set RUN_HF_INTEGRATION=1 to download the full ~574MB dataset.",
)


def test_load_raw_small_slice() -> None:
    from src.phases.phase01.loader import load_raw

    df = load_raw(max_rows=50)
    assert len(df) == 50
    assert "name" in df.columns

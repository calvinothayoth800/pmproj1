"""
Phase 01 — Hugging Face ingest.

Roll back this phase by removing ``src/phases/phase01`` and any callers (see ``meta.ROLLBACK``
in registry). Tracebacks under ``src.phases.phase01.loader`` attribute bugs to Phase 01.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import pandas as pd

logger = logging.getLogger(__name__)

HF_DATASET_NAME = "ManikaSaini/zomato-restaurant-recommendation"


def _resolve_split(ds: Any) -> Any:
    """Return a single ``datasets.Dataset`` from a Dataset or DatasetDict."""
    if hasattr(ds, "column_names"):
        return ds
    keys = getattr(ds, "keys", lambda: [])()
    if "train" in keys:
        return ds["train"]
    if keys:
        return ds[next(iter(keys))]
    raise ValueError("Unrecognized Hugging Face dataset structure (no splits).")


def load_raw(max_rows: Optional[int] = None) -> pd.DataFrame:
    """
    Download (or load from cache) the dataset and return a pandas DataFrame.

    Args:
        max_rows: If set, only take the first N rows after load (smoke tests / dev).

    Raises:
        RuntimeError: After repeated download failures.
    """
    from datasets import load_dataset

    last_err: Optional[BaseException] = None
    for attempt in range(3):
        try:
            try:
                split = load_dataset(HF_DATASET_NAME, split="train", trust_remote_code=False)
            except Exception:
                bundle = load_dataset(HF_DATASET_NAME, trust_remote_code=False)
                split = _resolve_split(bundle)
            df = split.to_pandas()
            if max_rows is not None:
                df = df.iloc[:max_rows].copy()
            logger.info("Loaded Hugging Face dataset %s rows=%s", HF_DATASET_NAME, len(df))
            return df
        except Exception as exc:  # noqa: BLE001 — surface after retries
            last_err = exc
            wait = 2**attempt
            logger.warning("HF load attempt %s failed: %s; retry in %ss", attempt + 1, exc, wait)
            time.sleep(wait)
    raise RuntimeError(f"Failed to load {HF_DATASET_NAME} after retries") from last_err

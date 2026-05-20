"""
Phase 01 — Parquet cache + metadata sidecar.

Changing ``CACHE_VERSION`` invalidates old artifacts on disk (real-world migration hook).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

CACHE_VERSION = "1"


def _meta_path(parquet_path: Path) -> Path:
    """Sidecar metadata next to parquet: ``restaurants.parquet.meta.json``."""
    return parquet_path.with_name(parquet_path.name + ".meta.json")


def save_processed(df: pd.DataFrame, path: Path, *, extra_meta: dict[str, Any] | None = None) -> None:
    """Write Parquet plus ``.meta.json`` with version and row counts."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    meta: dict[str, Any] = {
        "cache_version": CACHE_VERSION,
        "phase_id": "01",
        "rows": int(len(df)),
        "columns": list(df.columns),
        "written_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if extra_meta:
        meta.update(extra_meta)
    meta_path = _meta_path(path)
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    logger.info("Wrote cache parquet=%s meta=%s rows=%s", path, meta_path, len(df))


def load_processed(path: Path) -> pd.DataFrame:
    """Load Parquet; logs a warning if metadata version mismatches."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Cache not found: {path}")
    meta_path = _meta_path(path)
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        ver = meta.get("cache_version")
        if ver != CACHE_VERSION:
            logger.warning(
                "Cache metadata version %s != expected %s — rebuild with scripts/build_cache.py",
                ver,
                CACHE_VERSION,
            )
    df = pd.read_parquet(path)
    logger.info("Loaded cache rows=%s from %s", len(df), path)
    return df

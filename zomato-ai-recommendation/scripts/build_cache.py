#!/usr/bin/env python3
"""Download HF Zomato data, preprocess, and write Parquet cache (Phase 01 entrypoint)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

if sys.version_info < (3, 10):
    raise RuntimeError(
        "Python 3.10 or newer is required to run scripts/build_cache.py. "
        "Use `py -3 scripts/build_cache.py` or install Python 3.10+.`"
    )

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DATA_CACHE_PATH, PROJECT_ROOT  # noqa: E402
from src.phases.phase01 import CACHE_VERSION, load_raw, preprocess, save_processed  # noqa: E402

logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build processed restaurant Parquet cache.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_CACHE_PATH,
        help=f"Parquet output path (default: {DATA_CACHE_PATH})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild even if cache exists (removes existing parquet/meta).",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Only process first N rows after download (debug / CI smoke).",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    out_path = args.output
    if not out_path.is_absolute():
        out_path = PROJECT_ROOT / out_path

    meta_path = out_path.with_name(out_path.name + ".meta.json")
    if args.force:
        if out_path.is_file():
            out_path.unlink()
            logger.info("Removed existing parquet %s", out_path)
        if meta_path.is_file():
            meta_path.unlink()
            logger.info("Removed existing meta %s", meta_path)

    logger.info("Downloading / loading dataset (HF); cache_version=%s", CACHE_VERSION)
    raw_df = load_raw(max_rows=args.max_rows)
    logger.info("Raw rows=%s cols=%s", len(raw_df), len(raw_df.columns))

    processed, diag = preprocess(raw_df, dedupe=True)
    logger.info(
        "Processed rows=%s diagnostics=%s",
        len(processed),
        diag,
    )

    save_processed(processed, out_path, extra_meta={"diagnostics": diag})
    logger.info("Done. Wrote %s", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

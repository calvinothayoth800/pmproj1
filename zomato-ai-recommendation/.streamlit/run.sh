#!/usr/bin/env bash
set -e

DATA_CACHE="data/processed/restaurants.parquet"
if [ ! -f "$DATA_CACHE" ]; then
  echo "Building data cache..."
  python scripts/build_cache.py
fi

streamlit run src/ui/streamlit_app.py

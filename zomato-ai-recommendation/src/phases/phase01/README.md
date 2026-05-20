# Phase 01 — Data foundation (canonical package)

**Implementation lives here:** `loader.py`, `preprocessor.py`, `cache.py`, `restaurant_record.py`.

- **Traceability:** stack traces show `src.phases.phase01.*`.
- **Rollback:** delete `src/phases/phase01` and fix imports (see `src/phases/registry.py` manifests).
- **Compatibility:** `src/data/__init__.py` re-exports the same symbols for older snippets.

Phase dependency: **`phase00`** (`apply_city_aliases` only).

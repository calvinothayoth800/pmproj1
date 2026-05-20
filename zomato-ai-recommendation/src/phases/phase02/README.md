# Phase 02 — Filtering engine

Vectorized filters on the Phase 01 Parquet schema → capped candidate list + `to_llm_payload()` for Phase 03.

**Rollback:** remove `src/phases/phase02` and stop importing `FilterEngine`; Phase 03 prompts lose structured candidates unless reworked.

**Depends on:** Phase 01 dataframe columns (`city`, `budget_tier`, `cuisines`, …), Phase 00 `UserPreferences`.

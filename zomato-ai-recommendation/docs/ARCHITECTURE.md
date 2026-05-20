# Architecture: Zomato AI Restaurant Recommendation System

## Design Goals

1. **Minimize LLM cost and latency** — Never send 51K rows to the model; filter in Python/SQL first.
2. **Reproducible data** — Cache preprocessed data locally; version the cache.
3. **Testable layers** — Data, filter, LLM, and UI are separate modules with clear contracts.
4. **Graceful degradation** — If the LLM fails, return rule-based top-N from the filter layer.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                               │
│  Streamlit app (MVP)  OR  FastAPI + lightweight frontend (production) │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ UserPreferences, RecommendationResponse
┌───────────────────────────────────▼─────────────────────────────────────┐
│                      ORCHESTRATION (recommendation_service)              │
│  validate input → filter → build prompt → call LLM → parse → format out  │
└───────┬─────────────────────────────┬───────────────────────────┬───────┘
        │                             │                           │
┌───────▼────────┐          ┌─────────▼─────────┐        ┌────────▼────────┐
│  FILTER LAYER  │          │    LLM LAYER      │        │  FALLBACK RANK  │
│  (pandas/      │  JSON    │  OpenAI /         │        │  votes × rating │
│   optional     │ ───────► │  Anthropic /      │        │  if LLM down    │
│   SQLite)      │  top 30  │  local Ollama     │        └─────────────────┘
└───────┬────────┘          └───────────────────┘
        │
┌───────▼────────┐
│   DATA LAYER   │
│  HF load once  │
│  → clean       │
│  → parquet     │
│  cache         │
└────────────────┘
```

---

## Layer Responsibilities

### 1. Data Layer (`src/data/`)

| Component | Responsibility |
|-----------|----------------|
| `loader.py` | Download/load from Hugging Face `datasets` API; optional local CSV/Parquet override |
| `preprocessor.py` | Normalize `rate` (string → float), `approx_cost` (string → numeric + budget bucket), split `cuisines`, map `listed_in(city)` to canonical city |
| `cache.py` | Write/read `data/processed/restaurants.parquet`; invalidate on schema version bump |
| `schema.py` | Pydantic/dataclass `RestaurantRecord` — single source of truth for downstream fields |

**Efficiency choices**

- Load dataset **once** at startup (or lazy on first request with file lock).
- Keep only columns needed for filtering + LLM context (~12 fields, not `reviews_list` / full `menu_item`).
- Precompute `budget_tier` (`low` / `medium` / `high`) from cost percentiles per city.

### 2. Filter Layer (`src/phases/phase02/`, facade `src/filter/`)

| Component | Responsibility |
|-----------|----------------|
| `engine.py` | `FilterEngine`: vectorized masks + funnel metrics + empty-state messages |
| `scorer.py` | Composite sort key before LLM (rating, votes, cuisine overlap, budget match) |
| `payloads.py` | `to_llm_payload()` — stable ids + compact dicts for prompts |

Uses **`UserPreferences`** from Phase 00 only (no duplicate preference models).

**Filter pipeline (order matters for performance)**

1. City / `listed_in(city)` or `location` match (broadest index first if using SQLite).
2. `rating >= min_rating`
3. Budget tier overlap
4. Cuisine substring / token match (any-of user cuisines)
5. Boolean flags: `online_order`, `rest_type` contains "Quick Bites", etc.
6. Sort by composite score; `head(N)` for LLM

**Why not LLM-first?** Sending even 500 full rows × long text blows token limits and adds seconds of latency. Structured filter → **~30 rows × ~200 tokens** is ideal for ranking prompts.

### 3. LLM Layer (`src/llm/`)

| Component | Responsibility |
|-----------|----------------|
| `prompt_builder.py` | System + user prompt with JSON candidate list and explicit output schema |
| `client.py` | Thin wrapper around provider SDK; retries, timeout, structured output mode |
| `parser.py` | Validate JSON array: `{ rank, name, cuisine, rating, estimated_cost, explanation }` |
| `ranker.py` | Orchestrate: build prompt → invoke → parse → merge with ground-truth rows (anti-hallucination) |

**Prompt strategy**

- **System**: You are a restaurant advisor; only recommend from the provided list; never invent restaurants.
- **User**: Preferences summary + compact JSON table of candidates (id, name, cuisines, rate, cost, votes, highlights).
- **Output**: Strict JSON schema (use `response_format` / JSON mode when available).
- **Post-process**: Match LLM `name` to filtered dataframe; drop hallucinations; fill missing fields from data.

**Model selection (pragmatic)**

| Environment | Model | Rationale |
|-------------|-------|-----------|
| Dev / demo | `gpt-4o-mini` or local `llama3` via Ollama | Cheap, fast enough for ranking |
| Quality-focused | `gpt-4o` | Better explanations and tie-breaking |

### 4. Presentation Layer (`src/ui/` or `app/`)

| Component | Responsibility |
|-----------|----------------|
| Streamlit `app.py` | Build form payload → `preferences_from_ui()` from `src.phases.phase00`; display cards |
| `formatters.py` | Human-readable cost, stars, bullet explanations |

**MVP**: Streamlit single file calling `RecommendationService.recommend(prefs)` where `prefs` is `UserPreferences` from Phase 00.

**Later**: FastAPI `POST /recommend` + optional React/Vite frontend for mobile-friendly UI.

### 5. Configuration (`src/config.py`)

- Environment variables: `OPENAI_API_KEY`, `LLM_MODEL`, `MAX_CANDIDATES`, `DATA_CACHE_PATH`
- No secrets in repo; `.env.example` only

---

## Data Flow (Request Lifecycle)

```
User submits form
    → UserPreferences validated (Pydantic)
    → FilterEngine.apply(df, prefs) → DataFrame (≤ MAX_CANDIDATES)
    → if empty: return friendly "no matches" + suggest relaxing filters
    → PromptBuilder.build(prefs, candidates)
    → LLMClient.complete(prompt) → raw JSON
    → Parser.validate_and_enrich(candidates_df, llm_json)
    → RecommendationResponse (top K with explanations)
    → UI renders cards
```

**Typical timings (target)**

| Step | Target |
|------|--------|
| Filter | < 100 ms |
| LLM | 2–8 s |
| Total UX | < 10 s with loading indicator |

---

## Module Structure (target `src/` layout)

```
src/
├── __init__.py
├── config.py
├── phases/
│   ├── registry.py       # Ordered manifests: ids, deps, rollback hints
│   ├── phase00/          # Web UI contracts (+ meta.py)
│   │   ├── preferences.py
│   │   ├── ui_bridge.py
│   │   └── output_contract.py
│   └── phase01/          # Data foundation — loader / preprocessor / cache / schema
│       ├── loader.py
│       ├── preprocessor.py
│       ├── cache.py
│       └── restaurant_record.py
│   └── phase02/          # Filtering engine — masks, scorer, LLM payload shaping
│       ├── engine.py
│       ├── scorer.py
│       └── payloads.py
├── models/
│   └── restaurant.py     # Thin re-export of phase01 RestaurantRecord (optional)
├── data/
│   └── __init__.py       # Facade re-exporting phase01 (compat; prefer src.phases.phase01)
├── filter/
│   └── __init__.py           # Facade re-exporting phase02
├── llm/
│   ├── prompt_builder.py
│   ├── client.py
│   └── parser.py
├── services/
│   └── recommendation_service.py
└── ui/
    └── streamlit_app.py
```

---

## Key Design Decisions

| Decision | Choice | Alternative rejected |
|----------|--------|------------------------|
| Pre-LLM filtering | Pandas in-memory | Embedding search over 51K — overkill for structured prefs |
| Cache format | Parquet | Raw CSV reload every run — slow |
| LLM input size | 20–40 restaurants | Full city dump — token explosion |
| Hallucination control | ID/name match back to dataframe | Trust LLM names blindly |
| UI for MVP | Streamlit | Full SPA first — slower to ship |
| API shape | Single `recommend()` service method | Logic in UI — untestable |

---

## Security & Operations

- API keys via environment only; never log prompts containing PII (phone numbers stripped in preprocessor).
- Rate-limit LLM calls per session in UI (debounce submit button).
- Log filter counts and LLM latency (not full prompts in production).

---

## Extension Points (post-MVP)

- User history / collaborative filtering layer before LLM
- Vector DB for "vibe" queries ("romantic rooftop")
- Multi-city comparison and map view
- Caching identical preference hashes → skip LLM repeat calls

---

## Dependency Graph (implementation order)

```
Phase 1 (Data) ──► Phase 2 (Filter) ──► Phase 3 (LLM) ──► Phase 4 (UI) ──► Phase 5 (Hardening)
```

See [../phases.md](../phases.md) for deliverables per phase.

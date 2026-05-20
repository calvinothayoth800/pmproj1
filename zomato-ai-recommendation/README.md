# AI-Powered Restaurant Recommendation System (Zomato Use Case)

An application that combines structured restaurant data from Hugging Face with an LLM (Groq) to produce personalized, explainable restaurant recommendations.

## Problem Statement

Build a service that:

- Accepts user preferences (location, budget, cuisine, minimum rating, extras)
- Uses the [Zomato dataset](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) (~51K restaurants)
- Filters candidates efficiently, then uses an LLM to rank and explain choices
- Presents clear results (name, cuisine, rating, cost, AI explanation)

## Repository Layout

```
zomato-ai-recommendation/
├── README.md
├── pyproject.toml             # requires-python >= 3.10, pytest config
├── .python-version            # 3.11 (pyenv / IDE hint)
├── .env.example               # Copy to .env (includes Groq settings)
├── docs/
│   ├── ARCHITECTURE.md
│   ├── EDGE_CASES.md
│   ├── DATA_NOTES.md          # Phase 01: cached data / dropdowns
│   └── phases.md
├── scripts/
│   ├── build_cache.py         # Phase 01 CLI
│   └── try_filter.py          # Phase 02 CLI smoke test
├── src/
│   ├── phases/
│   │   ├── registry.py        # Phase order + rollback hints (start here for modularity story)
│   │   ├── phase00/           # UI contracts
│   │   └── phase01/           # Data ingest + cache (canonical implementation)
│   ├── data/__init__.py       # Facade re-exporting phase01 (compat)
│   └── ...
├── data/                      # Cached parquet (gitignored)
└── requirements.txt
```

## Environment (Groq)

```bash
copy .env.example .env
```

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Groq API key (`gsk_...`) |
| `LLM_PROVIDER` | `groq` (default) |
| `LLM_MODEL` | e.g. `llama-3.3-70b-versatile` |
| `LLM_BASE_URL` | `https://api.groq.com/openai/v1` |

**Security:** `.env` is gitignored. If you publish the repo, remove the real key from `.env.example` and rotate the key in the [Groq console](https://console.groq.com/).

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — includes phased `src/` layout
- [Development phases](docs/phases.md)
- [Phase registry](src/phases/registry.py) — dependency order + rollback hints in code
- [Edge cases](docs/EDGE_CASES.md)
- [Data notes / dropdown prep](docs/DATA_NOTES.md)

## Requirements

- **Python 3.10+** (project pins **3.11** in `.python-version`; use `py -3.11` on Windows if `python` still points to an older install)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py -3.11 -m pytest tests/
```

### Phase 01 — build data cache

Downloads from Hugging Face (~574 MB first run):

```powershell
py -3.11 scripts/build_cache.py
# Quick smoke (subset):
py -3.11 scripts/build_cache.py --max-rows 500 --force
```

Output: `data/processed/restaurants.parquet` (+ `.meta.json`). See [docs/DATA_NOTES.md](docs/DATA_NOTES.md).

## Dataset

| Source | Rows | Key fields |
|--------|------|------------|
| `ManikaSaini/zomato-restaurant-recommendation` | ~51,717 | `name`, `location`, `listed_in(city)`, `cuisines`, `rate`, `approx_cost(for two people)`, … |

## Status

| Phase | Status |
|-------|--------|
| 00 – Web UI contract (`src/phases/phase00`) | Implemented |
| 01 – Data foundation (`src/phases/phase01`, facade `src/data`) | Implemented |
| 02 – Filtering engine (`src/phases/phase02`, facade `src/filter`) | Implemented |
| 03 – LLM recommendation | Not started |
| 04 – User interface | Not started |
| 05 – Hardening & deploy | Not started |

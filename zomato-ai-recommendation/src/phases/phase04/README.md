# Phase 04 — User interface

End-to-end Streamlit application that integrates all previous phases into a cohesive user experience.

**Rollback:** remove `src/ui/` directory and stop running the Streamlit app; all backend logic in Phases 01–03 remains unaffected.

**Depends on:** Phase 00 (UI contracts), Phase 01 (data cache), Phase 02 (filter engine), Phase 03 (LLM recommendation service).

## Contents

| Module | Role |
|--------|------|
| `src/ui/streamlit_app.py` | Main Streamlit application with sidebar form and results display |
| `src/ui/formatters.py` | Display helpers for formatting costs, ratings, cuisines, and recommendation cards |

## Features

- **Dynamic filtering** — Real-time match counter shows how many restaurants match current filters
- **Smart cuisine dropdown** — Only shows cuisines available in the selected city with restaurant counts
- **Loading states** — Spinner during LLM recommendation generation
- **Rich result cards** — Display name, rating, cost, location, cuisines, popular dishes, badges, and AI explanation
- **Empty state handling** — Guidance when no restaurants match filters
- **Summary block** — Shows total candidates filtered and whether AI ranking was used

## Running the application

```bash
# Ensure data cache exists
python scripts/build_cache.py

# Set Groq API key in .env (copy from .env.example)
copy .env.example .env
# Edit .env and add your GROQ_API_KEY

# Launch Streamlit
streamlit run src/ui/streamlit_app.py
```

## UI Layout

### Sidebar — Preferences Form
- **City / Area** — Dropdown with restaurant counts (e.g., "Whitefield (807)")
- **Budget Tier** — Select from low/medium/high
- **Cuisines** — Multi-select with dynamic options based on selected city
- **Minimum Rating** — Slider from 0.0 to 5.0
- **Extras** — Checkboxes for family-friendly, quick service, table booking
- **Number of Results** — Slider to control top-K recommendations (1-10)

### Main Area
- **Live match counter** — Updates as filters change (green/yellow/red based on match count)
- **Results section** — Summary block followed by numbered recommendation cards
- **Each card shows:**
  - Rank and restaurant name
  - Rating and estimated cost for two
  - Location
  - Cuisine tags
  - Popular dishes (if available)
  - Badges (online order, book table, review count)
  - AI-generated explanation

## Integration Points

The Streamlit app integrates with all previous phases:

1. **Phase 00** — Uses `UserPreferences`, `preferences_from_ui_safe()`, and `RecommendationResponse` types
2. **Phase 01** — Loads cached parquet via `load_processed()` with `@st.cache_resource`
3. **Phase 02** — Uses `FilterEngine` for live match counting
4. **Phase 03** — Calls `RecommendationService.recommend()` for final recommendations

## Caching Strategy

- `@st.cache_resource` — DataFrame loaded once per server session
- `@st.cache_data` — City counts and cuisine counts cached per session
- No caching on recommendation calls (always fresh from LLM)

## Error Handling

- Missing data cache → Error message with instructions to run `build_cache.py`
- Validation errors → Displayed inline from `preferences_from_ui_safe()`
- Empty results → Warning with suggestions to relax filters
- LLM failures → Fallback to scorer-based ranking with badge indicating "Scorer-ranked (LLM offline)"
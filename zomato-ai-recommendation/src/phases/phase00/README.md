# Phase 00 — Web UI contract

**Purpose:** stable **input** and **output** types for the Streamlit (or API) layer, so Phase 04 can be built against real models before Phase 01–03 exist.

## Contents

| Module | Role |
|--------|------|
| `preferences.py` | `UserPreferences`, `BudgetTier`, `PreferenceExtras` |
| `ui_bridge.py` | `preferences_from_ui()`, city aliases, cuisine caps |
| `output_contract.py` | `RecommendationItem`, `RecommendationResponse` |

## Rollback

1. Delete the folder `src/phases/phase00/`.
2. Remove `phase00` exports from `src/phases/phase00/__init__.py` parent re-exports if any.
3. Search the repo for `src.phases.phase00` and delete or replace imports.

Later phases should **import** these types rather than copying them, so rollback of Phase 00 only affects the contract until you restore the folder.

## Web UI integration (Phase 04)

After form submit, build a dict and parse:

```python
from src.phases.phase00 import preferences_from_ui_safe, RecommendationResponse

payload = {
    "city": city_widget,
    "budget": budget_radio,  # "low" | "medium" | "high"
    "cuisines": cuisine_multiselect,
    "min_rating": float(rating_slider),
    "extras": {
        "family_friendly": fam_cb,
        "quick_service": quick_cb,
        "book_table": book_cb,
    },
}
prefs, errors = preferences_from_ui_safe(payload)
if errors:
    st.error("; ".join(errors))
else:
    # later: service.recommend(prefs)
    st.json(prefs.model_dump())
```

Until the pipeline exists, use `RecommendationResponse.not_implemented_placeholder()`.

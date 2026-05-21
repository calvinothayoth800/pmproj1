"""Zomato AI Restaurant Recommendation — Streamlit UI (Phase 04)."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Ensure project root on sys.path so `src.*` imports work regardless of cwd.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import DATA_CACHE_PATH, LLM_API_KEY, LLM_PROVIDER, PROJECT_ROOT, TOP_K_RECOMMENDATIONS
from src.phases.phase00.preferences import UserPreferences, PreferenceExtras
from src.phases.phase00.ui_bridge import preferences_from_ui_safe
from src.phases.phase01.cache import load_processed
from src.phases.phase02.engine import FilterEngine
from src.llm.client import get_last_call_info
from src.services.recommendation_service import RecommendationService
from src.ui.formatters import item_card_markdown, response_summary_markdown

# ---------------------------------------------------------------------------
# Cached data loader (loaded once per server session)
# ---------------------------------------------------------------------------

@st.cache_resource
def _load_dataframe() -> "pd.DataFrame":
    """Load the processed Parquet cache once and share across sessions."""
    import pandas as pd  # noqa: avoid top-level heavy import
    import subprocess

    path = DATA_CACHE_PATH
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        build_script = PROJECT_ROOT / "scripts" / "build_cache.py"
        if build_script.is_file():
            st.info("No local cache was found. Building it now may take a few minutes.")
            with st.spinner("Building restaurant cache..."):
                try:
                    subprocess.run(
                        [sys.executable, str(build_script)],
                        check=True,
                        cwd=str(PROJECT_ROOT),
                        capture_output=True,
                        text=True,
                    )
                except subprocess.CalledProcessError as exc:
                    st.error(
                        "Automatic cache build failed. Please ensure Python 3.10+ is installed "
                        "and the deployment environment has network access, then restart the app."
                    )
                    if exc.stdout:
                        st.code(exc.stdout, language="text")
                    if exc.stderr:
                        st.code(exc.stderr, language="text")
                    st.stop()
        else:
            st.error(
                "Data cache not found and no build script is available. "
                "Run `python scripts/build_cache.py` locally or restore the cache file."
            )
            st.stop()

        if not path.exists():
            st.error(
                "Data cache still missing after build. Run `python scripts/build_cache.py` locally "
                "or check the file path in DATA_CACHE_PATH."
            )
            st.stop()
    return load_processed(path)


@st.cache_data
def _city_counts(_df: "pd.DataFrame") -> dict[str, int]:
    """Map city name → restaurant count."""
    return _df["city"].value_counts().to_dict()


@st.cache_data
def _cuisine_counts_for_city(_df: "pd.DataFrame", city: str) -> dict[str, int]:
    """Map cuisine token → count, restricted to rows in the given city."""
    subset = _df[_df["city"] == city]
    counts: dict[str, int] = {}
    for cell in subset["cuisines"].dropna():
        for t in str(cell).split("|"):
            t = t.strip()
            if t:
                counts[t] = counts.get(t, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Zomato AI Recommender",
    page_icon="🍽️",
    layout="wide",
)

st.title("🍽️ Zomato AI Restaurant Recommender")
st.caption("Get personalized restaurant picks powered by AI — filtered from 12K+ Zomato listings.")
if LLM_API_KEY:
    st.info(f"LLM provider configured: {LLM_PROVIDER.upper()}. Recommendations will use the Groq API if available.")
else:
    st.warning("GROQ_API_KEY is not configured. The app will return structured fallback recommendations instead of AI-ranked results.")

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

df = _load_dataframe()
city_counts = _city_counts(df)

# City options with counts: "Whitefield (807)"
city_labels = {c: f"{c} ({city_counts.get(c, 0)})" for c in sorted(city_counts)}
city_names = list(city_labels.keys())

# ---------------------------------------------------------------------------
# Sidebar — preference form
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Preferences")

    city = st.selectbox(
        "City / Area",
        options=city_names,
        format_func=lambda c: city_labels[c],
    )

    budget = st.selectbox("Budget Tier", options=["low", "medium", "high"], index=1)

    # Dynamic cuisine list — only cuisines available in the selected city, with counts
    cuisine_counts = _cuisine_counts_for_city(df, city)
    cuisine_options = sorted(cuisine_counts.keys())

    selected_cuisines = st.multiselect(
        "Cuisines",
        options=cuisine_options,
        default=[],
        help="Leave empty to skip cuisine filtering. Counts show restaurants in this city.",
        format_func=lambda x: f"{x.title()} ({cuisine_counts.get(x, 0)})",
    )

    min_rating = st.slider(
        "Minimum Rating",
        min_value=0.0,
        max_value=5.0,
        value=0.0,
        step=0.1,
        help="Set to 0 to include unrated restaurants.",
    )

    st.divider()
    st.subheader("Extras")

    family_friendly = st.checkbox("Family Friendly", value=False)
    quick_service = st.checkbox("Quick Service", value=False)
    book_table = st.checkbox("Table Booking Available", value=False)

    st.divider()

    top_k = st.slider(
        "Number of Results",
        min_value=1,
        max_value=10,
        value=TOP_K_RECOMMENDATIONS,
    )

    submitted = st.button("🔍 Get Recommendations", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Main area — live counter + results
# ---------------------------------------------------------------------------

# Live match counter — shows how many restaurants fit as you adjust filters
filter_payload = {
    "city": city,
    "budget": budget,
    "cuisines": selected_cuisines,
    "min_rating": min_rating,
    "extras": {
        "family_friendly": family_friendly,
        "quick_service": quick_service,
        "book_table": book_table,
    },
}
live_prefs, live_errors = preferences_from_ui_safe(filter_payload)

if live_prefs is not None:
    _engine = FilterEngine(df)
    _result = _engine.apply(live_prefs, log_steps=False)
    match_count = _result.funnel.get("after_extras", 0)

    if match_count == 0:
        st.error(f"**0 restaurants match** — relax your filters before clicking")
    elif match_count <= 3:
        st.warning(f"**{match_count} restaurant{'s' if match_count != 1 else ''} match** — limited options")
    else:
        st.success(f"**{match_count} restaurants match** your filters")
else:
    st.error("Invalid filter combination")

if not submitted:
    st.info("Adjust your filters, then click **Get Recommendations** when ready.")
    st.stop()

# Build preferences via the safe bridge (surfaces validation errors)
payload = {
    "city": city,
    "budget": budget,
    "cuisines": selected_cuisines,
    "min_rating": min_rating,
    "extras": {
        "family_friendly": family_friendly,
        "quick_service": quick_service,
        "book_table": book_table,
    },
}

prefs, errors = preferences_from_ui_safe(payload)

if errors:
    for err in errors:
        st.error(err)
    st.stop()

# Run recommendation
service = RecommendationService(df)

with st.spinner("Finding the best restaurants for you..."):
    response = service.recommend(prefs, top_k=top_k)

if response.llm_used:
    st.success("AI-ranked recommendations generated using Groq.")
else:
    st.warning("Structured fallback recommendations are being shown. Check your GROQ_API_KEY or network if you expected Groq to be used.")

call_info = get_last_call_info()
if call_info:
    with st.expander("LLM diagnostics"):
        st.json(call_info)

# ---- Render results ----

if not response.items:
    st.warning("No restaurants match your filters.")
    if response.messages:
        for msg in response.messages:
            st.info(msg)
    st.caption("Try relaxing your budget, lowering the minimum rating, or removing a cuisine filter.")
    st.stop()

# Summary block
st.markdown(response_summary_markdown(response))

# Result cards
for item in response.items:
    st.markdown(item_card_markdown(item))

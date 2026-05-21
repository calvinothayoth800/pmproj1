"""Zomato AI Restaurant Recommendation Streamlit UI."""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

# Ensure project root on sys.path so `src.*` imports work regardless of cwd.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config import DATA_CACHE_PATH, PROJECT_ROOT, TOP_K_RECOMMENDATIONS
from src.phases.phase00.ui_bridge import preferences_from_ui_safe
from src.phases.phase01.cache import load_processed
from src.phases.phase02.engine import FilterEngine
from src.services.recommendation_service import RecommendationService
from src.ui.formatters import item_card_markdown, response_summary_markdown


@st.cache_resource
def _load_dataframe() -> "pd.DataFrame":
    """Load the processed Parquet cache once and share across sessions."""
    import pandas as pd  # noqa: F401 - used by the return type at runtime in Streamlit
    import subprocess

    path = DATA_CACHE_PATH
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not path.exists():
        build_script = PROJECT_ROOT / "scripts" / "build_cache.py"
        if build_script.is_file():
            with st.spinner("Preparing restaurant data..."):
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
    """Map city name to restaurant count."""
    return _df["city"].value_counts().to_dict()


@st.cache_data
def _cuisine_counts_for_city(_df: "pd.DataFrame", city: str) -> dict[str, int]:
    """Map cuisine token to count, restricted to rows in the given city."""
    subset = _df[_df["city"] == city]
    counts: dict[str, int] = {}
    for cell in subset["cuisines"].dropna():
        for token in str(cell).split("|"):
            token = token.strip()
            if token:
                counts[token] = counts.get(token, 0) + 1
    return counts


st.set_page_config(
    page_title="Zomato AI Recommender",
    layout="centered",
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 980px;
        padding-top: 2.2rem;
        padding-bottom: 3rem;
    }
    [data-testid="stSidebar"] {
        display: none;
    }
    .app-title {
        text-align: center;
        margin-bottom: 0.35rem;
    }
    .app-subtitle {
        color: #8a94a6;
        text-align: center;
        margin-bottom: 1.5rem;
    }
    .section-label {
        color: #8a94a6;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        margin: 0.2rem 0 0.7rem;
        text-transform: uppercase;
    }
    div[data-testid="stForm"] {
        border: 1px solid rgba(148, 163, 184, 0.22);
        border-radius: 10px;
        padding: 1.2rem 1.35rem 1.35rem;
        background: rgba(15, 23, 42, 0.35);
    }
    div[data-testid="stForm"] button {
        min-height: 2.8rem;
    }
    .results-heading {
        margin-top: 2rem;
        margin-bottom: 0.35rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h1 class='app-title'>Zomato AI Restaurant Recommender</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='app-subtitle'>Set your preferences and get a focused restaurant shortlist.</p>",
    unsafe_allow_html=True,
)

df = _load_dataframe()
city_counts = _city_counts(df)
city_labels = {city: f"{city} ({city_counts.get(city, 0)})" for city in sorted(city_counts)}
city_names = list(city_labels.keys())

with st.form("recommendation_preferences", clear_on_submit=False):
    st.markdown("<div class='section-label'>Your preferences</div>", unsafe_allow_html=True)

    row1_col1, row1_col2, row1_col3 = st.columns([2.2, 1, 1])
    with row1_col1:
        city = st.selectbox(
            "City / Area",
            options=city_names,
            format_func=lambda option: city_labels[option],
        )
    with row1_col2:
        budget = st.selectbox("Budget", options=["low", "medium", "high"], index=1)
    with row1_col3:
        top_k = st.slider(
            "Results",
            min_value=1,
            max_value=10,
            value=TOP_K_RECOMMENDATIONS,
        )

    cuisine_counts = _cuisine_counts_for_city(df, city)
    cuisine_options = sorted(cuisine_counts.keys())
    selected_cuisines = st.multiselect(
        "Cuisines",
        options=cuisine_options,
        default=[],
        help="Leave empty to include all cuisines available in the selected area.",
        format_func=lambda option: f"{option.title()} ({cuisine_counts.get(option, 0)})",
    )

    rating_col, extras_col = st.columns([1, 1.4])
    with rating_col:
        min_rating = st.slider(
            "Minimum rating",
            min_value=0.0,
            max_value=5.0,
            value=0.0,
            step=0.1,
            help="Set to 0 to include unrated restaurants.",
        )
    with extras_col:
        st.caption("Extras")
        extra_col1, extra_col2, extra_col3 = st.columns(3)
        with extra_col1:
            family_friendly = st.checkbox("Family", value=False)
        with extra_col2:
            quick_service = st.checkbox("Quick service", value=False)
        with extra_col3:
            book_table = st.checkbox("Table booking", value=False)

    submitted = st.form_submit_button("Get recommendations", type="primary", use_container_width=True)

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
    filter_result = FilterEngine(df).apply(live_prefs, log_steps=False)
    match_count = filter_result.funnel.get("after_extras", 0)

    if match_count == 0:
        st.error("0 restaurants match these filters. Relax one or two preferences.")
    elif match_count <= 3:
        st.warning(f"{match_count} restaurant{'s' if match_count != 1 else ''} match these filters.")
    else:
        st.success(f"{match_count} restaurants match these filters.")
else:
    st.error("Invalid filter combination.")

if not submitted:
    st.stop()

prefs, errors = preferences_from_ui_safe(filter_payload)
if errors:
    for err in errors:
        st.error(err)
    st.stop()

service = RecommendationService(df)
with st.spinner("Finding the best restaurants for you..."):
    response = service.recommend(prefs, top_k=top_k)

st.markdown("<h2 class='results-heading'>Recommended restaurants</h2>", unsafe_allow_html=True)
if response.llm_used:
    st.caption("Ranked with Groq AI.")
else:
    st.caption("Ranked with the local scoring engine.")

if not response.items:
    st.warning("No restaurants match your filters.")
    if response.messages:
        for msg in response.messages:
            st.info(msg)
    st.caption("Try relaxing your budget, lowering the minimum rating, or removing a cuisine filter.")
    st.stop()

st.markdown(response_summary_markdown(response))

for item in response.items:
    st.markdown(item_card_markdown(item))

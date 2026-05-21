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
    :root {
        --bg: #070a12;
        --panel: #101624;
        --panel-soft: #131b2c;
        --line: rgba(148, 163, 184, 0.20);
        --text-soft: #9aa7bb;
        --text-faint: #657086;
        --accent: #ff5a3d;
        --accent-2: #22c55e;
        --gold: #f6c85f;
    }
    html, body, [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 18% 0%, rgba(255, 90, 61, 0.16), transparent 30rem),
            radial-gradient(circle at 88% 8%, rgba(34, 197, 94, 0.11), transparent 26rem),
            var(--bg);
    }
    .block-container {
        max-width: 1040px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }
    [data-testid="stSidebar"] {
        display: none;
    }
    .app-title {
        text-align: center;
        margin-bottom: 0.35rem;
        font-size: clamp(2.05rem, 5vw, 4rem);
        line-height: 1.02;
        font-weight: 850;
        color: #f8fafc;
    }
    .app-subtitle {
        color: var(--text-soft);
        text-align: center;
        margin: 0 auto 1.8rem;
        max-width: 680px;
        font-size: 1.02rem;
    }
    .section-label {
        color: #ffb199;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        margin: 0.2rem 0 0.85rem;
        text-transform: uppercase;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 1.3rem 1.35rem 1.45rem;
        background:
            linear-gradient(180deg, rgba(22, 31, 49, 0.92), rgba(13, 18, 31, 0.94));
        box-shadow: 0 22px 70px rgba(0, 0, 0, 0.32);
        margin-bottom: 1rem;
    }
    .control-hint {
        color: var(--text-soft);
        margin: -0.35rem 0 1.1rem;
        font-size: 0.94rem;
    }
    .match-card {
        border: 1px solid rgba(34, 197, 94, 0.28);
        border-radius: 12px;
        background: rgba(34, 197, 94, 0.10);
        padding: 0.95rem 1.05rem;
        margin: 0.8rem 0 1rem;
    }
    .match-card.warn {
        border-color: rgba(246, 200, 95, 0.38);
        background: rgba(246, 200, 95, 0.10);
    }
    .match-card.danger {
        border-color: rgba(248, 113, 113, 0.40);
        background: rgba(248, 113, 113, 0.10);
    }
    .match-number {
        color: #f8fafc;
        font-size: 1.7rem;
        font-weight: 800;
        line-height: 1;
    }
    .match-label {
        color: var(--text-soft);
        margin-top: 0.3rem;
    }
    div[data-testid="stSelectbox"] label,
    div[data-testid="stMultiSelect"] label,
    div[data-testid="stSlider"] label,
    div[data-testid="stRadio"] label,
    div[data-testid="stCheckbox"] label,
    div[data-testid="stToggle"] label {
        color: #dbe4f0 !important;
        font-weight: 650;
    }
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        border-color: rgba(148, 163, 184, 0.22) !important;
        background-color: rgba(7, 10, 18, 0.55) !important;
        border-radius: 10px !important;
    }
    div[data-testid="stMultiSelect"] [data-baseweb="tag"] {
        background-color: rgba(255, 90, 61, 0.18) !important;
        border: 1px solid rgba(255, 90, 61, 0.26);
        border-radius: 999px;
    }
    .stButton > button {
        min-height: 2.8rem;
        border-radius: 10px;
        border: 0;
        background: linear-gradient(135deg, #ff6a3d, #ff3d5a);
        font-weight: 750;
        box-shadow: 0 16px 34px rgba(255, 90, 61, 0.22);
    }
    div[data-testid="stToggle"] {
        background: rgba(7, 10, 18, 0.38);
        border: 1px solid rgba(148, 163, 184, 0.14);
        border-radius: 12px;
        min-height: 72px;
        padding: 0.72rem 0.78rem;
    }
    div[data-testid="stToggle"] label {
        align-items: center;
        display: flex;
        gap: 0.45rem;
        min-height: 38px;
    }
    div[data-testid="stToggle"] p {
        font-size: 0.9rem;
        line-height: 1.2;
        margin: 0;
    }
    .extras-grid-title {
        color: var(--text-soft);
        font-size: 0.86rem;
        font-weight: 700;
        margin: 0.1rem 0 0.45rem;
    }
    .results-heading {
        margin-top: 2.1rem;
        margin-bottom: 0.35rem;
        color: #f8fafc;
    }
    .summary-card {
        align-items: center;
        background: rgba(16, 22, 36, 0.82);
        border: 1px solid var(--line);
        border-radius: 14px;
        display: flex;
        gap: 1rem;
        justify-content: space-between;
        margin: 1rem 0 1.1rem;
        padding: 1rem 1.1rem;
    }
    .summary-card p {
        color: #dbe4f0;
        margin: 0.2rem 0 0;
    }
    .summary-kicker {
        color: var(--accent);
        font-size: 0.74rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .summary-count {
        border-left: 1px solid var(--line);
        min-width: 110px;
        padding-left: 1rem;
        text-align: right;
    }
    .summary-count strong {
        color: #f8fafc;
        display: block;
        font-size: 1.8rem;
        line-height: 1;
    }
    .summary-count span,
    .summary-note {
        color: var(--text-soft);
    }
    .result-card {
        align-items: flex-start;
        background:
            linear-gradient(135deg, rgba(19, 27, 44, 0.96), rgba(10, 15, 26, 0.96));
        border: 1px solid var(--line);
        border-radius: 14px;
        display: grid;
        gap: 1rem;
        grid-template-columns: 54px 1fr;
        margin: 0 0 0.9rem;
        padding: 1rem;
        box-shadow: 0 18px 42px rgba(0, 0, 0, 0.22);
    }
    .result-rank {
        align-items: center;
        background: rgba(255, 90, 61, 0.14);
        border: 1px solid rgba(255, 90, 61, 0.24);
        border-radius: 12px;
        color: #ffb199;
        display: flex;
        font-size: 1rem;
        font-weight: 850;
        height: 48px;
        justify-content: center;
    }
    .result-topline {
        align-items: flex-start;
        display: flex;
        gap: 1rem;
        justify-content: space-between;
    }
    .result-card h3 {
        color: #f8fafc;
        font-size: 1.15rem;
        line-height: 1.25;
        margin: 0;
    }
    .result-location {
        color: var(--text-soft);
        margin: 0.25rem 0 0;
    }
    .result-score {
        background: rgba(246, 200, 95, 0.12);
        border: 1px solid rgba(246, 200, 95, 0.28);
        border-radius: 12px;
        min-width: 74px;
        padding: 0.45rem 0.6rem;
        text-align: center;
    }
    .result-score strong {
        color: var(--gold);
        display: block;
        font-size: 1.18rem;
    }
    .result-score span,
    .result-meta,
    .result-dishes span {
        color: var(--text-faint);
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .result-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        margin: 0.8rem 0;
        text-transform: none;
        letter-spacing: 0;
        font-size: 0.93rem;
    }
    .result-meta span,
    .result-pill {
        background: rgba(148, 163, 184, 0.10);
        border: 1px solid rgba(148, 163, 184, 0.16);
        border-radius: 999px;
        color: #dbe4f0;
        padding: 0.34rem 0.62rem;
    }
    .result-dishes {
        color: #c8d2e0;
        margin-bottom: 0.75rem;
    }
    .result-dishes span {
        display: block;
        margin-bottom: 0.2rem;
    }
    .result-pills {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-bottom: 0.75rem;
    }
    .result-pill {
        font-size: 0.84rem;
    }
    .result-pill.accent {
        background: rgba(34, 197, 94, 0.11);
        border-color: rgba(34, 197, 94, 0.24);
        color: #86efac;
    }
    .result-explanation {
        border-left: 3px solid rgba(255, 90, 61, 0.65);
        color: #dbe4f0;
        margin: 0.8rem 0 0;
        padding-left: 0.85rem;
    }
    @media (max-width: 720px) {
        .summary-card,
        .result-topline {
            display: block;
        }
        .summary-count {
            border-left: 0;
            border-top: 1px solid var(--line);
            margin-top: 0.85rem;
            padding-left: 0;
            padding-top: 0.85rem;
            text-align: left;
        }
        .result-card {
            grid-template-columns: 1fr;
        }
        .result-rank {
            height: 38px;
            width: 54px;
        }
        .result-score {
            display: inline-block;
            margin-top: 0.7rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h1 class='app-title'>Zomato AI Restaurant Recommender</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='app-subtitle'>A focused shortlist of restaurants shaped around taste, budget, and dining style.</p>",
    unsafe_allow_html=True,
)

df = _load_dataframe()
city_counts = _city_counts(df)
city_labels = {city: f"{city} ({city_counts.get(city, 0)})" for city in sorted(city_counts)}
city_names = list(city_labels.keys())

with st.container(border=True):
    st.markdown("<div class='section-label'>Your preferences</div>", unsafe_allow_html=True)
    st.markdown(
        "<p class='control-hint'>Location, taste, budget, and service preferences.</p>",
        unsafe_allow_html=True,
    )

    row1_col1, row1_col2, row1_col3 = st.columns([2.2, 1, 1])
    with row1_col1:
        city = st.selectbox(
            "City / Area",
            options=city_names,
            format_func=lambda option: city_labels[option],
        )
    with row1_col2:
        budget = st.radio("Budget", options=["low", "medium", "high"], index=1, horizontal=True)
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
        st.markdown("<p class='extras-grid-title'>Extras</p>", unsafe_allow_html=True)
        extra_col1, extra_col2, extra_col3 = st.columns(3)
        with extra_col1:
            family_friendly = st.toggle("Family friendly", value=False)
        with extra_col2:
            quick_service = st.toggle("Quick service", value=False)
        with extra_col3:
            book_table = st.toggle("Table booking", value=False)

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
    match_count = 0
    if live_prefs is not None:
        filter_result = FilterEngine(df).apply(live_prefs, log_steps=False)
        match_count = filter_result.funnel.get("after_extras", 0)
        if match_count == 0:
            match_class = "danger"
            match_text = "No restaurants match yet. Relax one or two preferences."
        elif match_count <= 3:
            match_class = "warn"
            noun = "restaurant" if match_count == 1 else "restaurants"
            match_text = f"{match_count} {noun} match. The shortlist will be very tight."
        else:
            match_class = ""
            match_text = "restaurants match these filters."

        st.markdown(
            f"""
            <div class="match-card {match_class}">
                <div class="match-number">{match_count}</div>
                <div class="match-label">{match_text}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="match-card danger">
                <div class="match-number">0</div>
                <div class="match-label">Invalid filter combination.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    submitted = st.button("Get recommendations", type="primary", use_container_width=True)

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

if not response.items:
    st.warning("No restaurants match your filters.")
    if response.messages:
        for msg in response.messages:
            st.info(msg)
    st.caption("Try relaxing your budget, lowering the minimum rating, or removing a cuisine filter.")
    st.stop()

st.markdown(response_summary_markdown(response), unsafe_allow_html=True)

for item in response.items:
    st.markdown(item_card_markdown(item), unsafe_allow_html=True)

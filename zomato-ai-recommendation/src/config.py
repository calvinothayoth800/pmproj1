"""Application configuration loaded from environment / .env."""

from pathlib import Path

from dotenv import load_dotenv
import os
from typing import Optional

# Project root: zomato-ai-recommendation/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

load_dotenv(_ENV_PATH)


def _streamlit_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Read a top-level Streamlit secret when Streamlit is available."""
    try:
        import streamlit as st

        return st.secrets.get(key, default)
    except Exception:
        return default


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    """Read from environment; fall back to Streamlit secrets if available."""
    val = os.getenv(key)
    if val:
        return val

    # Try Streamlit secrets as fallback (for Streamlit Cloud / local .streamlit/secrets.toml).
    return _streamlit_secret(key, default)


def _env_int(key: str, default: int) -> int:
    raw = _env(key)
    if raw is None:
        return default
    return int(raw)


def get_llm_api_key() -> Optional[str]:
    """Read the active LLM API key at call time."""
    provider = (_env("LLM_PROVIDER", LLM_PROVIDER) or "groq").lower()
    groq_key = _env("GROQ_API_KEY")
    openai_key = _env("OPENAI_API_KEY")
    key = groq_key if provider == "groq" else openai_key
    return key or groq_key or openai_key


LLM_PROVIDER: str = (_env("LLM_PROVIDER", "groq") or "groq").lower()
GROQ_API_KEY: Optional[str] = _env("GROQ_API_KEY")
OPENAI_API_KEY: Optional[str] = _env("OPENAI_API_KEY")

# Groq uses GROQ_API_KEY; OpenAI uses OPENAI_API_KEY (OpenAI-compatible clients accept either)
LLM_API_KEY: Optional[str] = GROQ_API_KEY if LLM_PROVIDER == "groq" else OPENAI_API_KEY
if LLM_API_KEY is None:
    LLM_API_KEY = GROQ_API_KEY or OPENAI_API_KEY

LLM_MODEL: str = _env("LLM_MODEL", "llama-3.3-70b-versatile") or "llama-3.3-70b-versatile"
LLM_BASE_URL: str = (
    _env("LLM_BASE_URL", "https://api.groq.com/openai/v1") or "https://api.groq.com/openai/v1"
)

MAX_CANDIDATES: int = _env_int("MAX_CANDIDATES", 35)
TOP_K_RECOMMENDATIONS: int = _env_int("TOP_K_RECOMMENDATIONS", 5)

_default_cache = _PROJECT_ROOT / "data" / "processed" / "restaurants.parquet"
_cache_raw = _env("DATA_CACHE_PATH")
DATA_CACHE_PATH: Path = Path(_cache_raw) if _cache_raw else _default_cache
if not DATA_CACHE_PATH.is_absolute():
    DATA_CACHE_PATH = _PROJECT_ROOT / DATA_CACHE_PATH

PROJECT_ROOT: Path = _PROJECT_ROOT

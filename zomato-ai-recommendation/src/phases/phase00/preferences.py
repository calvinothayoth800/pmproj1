"""User preference models — primary input contract from the web UI."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

BudgetTier = Literal["low", "medium", "high"]


class PreferenceExtras(BaseModel):
    """Optional toggles mirrored by Streamlit checkboxes."""

    family_friendly: bool = False
    quick_service: bool = False
    book_table: bool = False


class UserPreferences(BaseModel):
    """
    Canonical payload produced by the web UI (Streamlit form → service).

    Phase 02+ filtering uses these fields; the LLM may receive ``additional_notes``.
    """

    city: str = Field(..., min_length=1, max_length=120)
    budget: BudgetTier
    cuisines: list[str] = Field(default_factory=list)
    min_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    extras: PreferenceExtras = Field(default_factory=PreferenceExtras)
    additional_notes: str | None = Field(default=None, max_length=4000)

    model_config = {"frozen": False}

    @field_validator("city")
    @classmethod
    def city_not_blank(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("city cannot be empty or whitespace")
        return s

    @field_validator("cuisines", mode="before")
    @classmethod
    def cuisines_coerce(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            # Single comma-separated string from a text box fallback
            parts = [p.strip() for p in v.split(",") if p.strip()]
            return parts
        if isinstance(v, (list, tuple)):
            return [str(x).strip() for x in v if str(x).strip()]
        raise TypeError("cuisines must be a list, tuple, or string")

    @field_validator("cuisines")
    @classmethod
    def cuisines_dedupe_preserve_order(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for c in v:
            key = c.casefold()
            if key not in seen:
                seen.add(key)
                out.append(c)
        return out

    def has_cuisine_filter(self) -> bool:
        return len(self.cuisines) > 0

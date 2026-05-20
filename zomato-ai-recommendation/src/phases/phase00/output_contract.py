"""Stable output shapes the web UI can render (populated by Phase 03+)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RecommendationItem(BaseModel):
    """One row in the results list shown in the UI."""

    rank: int = Field(..., ge=1)
    name: str
    cuisine: str = ""
    rating: float | None = None
    estimated_cost: int | None = Field(default=None, description="INR cost for two, if known")
    explanation: str = ""
    location: str = Field(default="", description="Sub-locality / neighbourhood")
    dish_liked: str = Field(default="", description="Popular dishes (pipe-separated)")
    book_table: bool = Field(default=False, description="Table booking available")
    online_order: bool = Field(default=False, description="Online ordering available")
    votes: int = Field(default=0, description="Number of user reviews/votes")


class RecommendationResponse(BaseModel):
    """
    Full response for the recommendation view.

    Phase 03+ fills ``items``; until then the UI can show ``messages`` only.
    """

    items: list[RecommendationItem] = Field(default_factory=list)
    summary: str | None = None
    filter_count: int | None = None
    llm_used: bool = False
    messages: list[str] = Field(
        default_factory=list,
        description="User-facing hints, e.g. empty filter reasons or API errors",
    )

    model_config = {"frozen": False}

    @classmethod
    def not_implemented_placeholder(cls) -> RecommendationResponse:
        """Use until pipeline is wired; keeps Streamlit layout testable."""
        return cls(
            items=[],
            messages=[
                "Recommendation pipeline not connected yet (Phase 01–03). "
                "Inputs were accepted; wire FilterEngine + LLM next."
            ],
        )

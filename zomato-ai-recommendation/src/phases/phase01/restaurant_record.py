"""Processed restaurant row schema — owned by Phase 01 (cache / filter input)."""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class RestaurantRecord(BaseModel):
    """Single row after Phase 01 preprocessing (Parquet-friendly types)."""

    restaurant_id: int = Field(..., ge=0)
    name: str
    city: str = ""
    location: str = ""
    cuisines: str = Field("", description="Pipe-separated normalized cuisine tokens")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    votes: int = Field(0, ge=0)
    cost_for_two: Optional[int] = Field(None, ge=0, description="Approximate INR for two")
    budget_tier: Optional[str] = Field(None, description="low | medium | high | unknown")
    rest_type: str = ""
    online_order: str = ""
    book_table: str = ""
    dish_liked: str = ""
    listed_in_type: str = ""

    def cuisine_list(self) -> list[str]:
        if not self.cuisines:
            return []
        return [p for p in (x.strip() for x in self.cuisines.split("|")) if p]

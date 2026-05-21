"""Human-readable display helpers for the Streamlit UI."""

from __future__ import annotations

from typing import Optional

from src.phases.phase00.output_contract import RecommendationItem, RecommendationResponse


def format_cost(cost: Optional[int]) -> str:
    """Format INR cost for two."""
    if cost is None:
        return "Price not listed"
    return f"INR {cost:,}"


def format_rating(rating: Optional[float]) -> str:
    """Format rating."""
    if rating is None:
        return "Rating N/A"
    return f"{rating:.1f}/5"


def format_cuisines(cuisine_str: str) -> list[str]:
    """Split pipe-separated cuisine string into displayable tags."""
    if not cuisine_str:
        return []
    return [token.strip().title() for token in cuisine_str.split("|") if token.strip()]


def format_dish_liked(dish_str: str) -> list[str]:
    """Split pipe-separated dish_liked into displayable tags."""
    if not dish_str:
        return []
    return [token.strip().title() for token in dish_str.split("|") if token.strip()]


def format_votes(votes: int) -> str:
    """Format vote count for display."""
    if votes <= 0:
        return ""
    if votes >= 1000:
        return f"{votes / 1000:.1f}K reviews"
    return f"{votes} reviews"


def item_card_markdown(item: RecommendationItem) -> str:
    """Build a markdown string for one recommendation card."""
    lines: list[str] = []

    lines.append(f"### {item.rank}. {item.name}")
    lines.append(f"**Rating:** {format_rating(item.rating)} &nbsp; **Cost for two:** {format_cost(item.estimated_cost)}")

    if item.location:
        lines.append(f"**Location:** {item.location}")

    cuisines = format_cuisines(item.cuisine)
    if cuisines:
        lines.append(f"**Cuisines:** {', '.join(cuisines)}")

    dishes = format_dish_liked(item.dish_liked)
    if dishes:
        lines.append(f"**Popular dishes:** {', '.join(dishes[:6])}")

    badges: list[str] = []
    if item.online_order:
        badges.append("Online ordering")
    if item.book_table:
        badges.append("Table booking")
    if item.votes > 0:
        badges.append(format_votes(item.votes))
    if badges:
        lines.append(f"**Available:** {' | '.join(badges)}")

    if item.explanation:
        lines.append(f"\n> {item.explanation}")

    lines.append("---")
    return "\n\n".join(lines)


def response_summary_markdown(response: RecommendationResponse) -> str:
    """Build a summary block for the top of the results."""
    parts: list[str] = []

    if response.summary:
        parts.append(f"**Summary:** {response.summary}")

    meta_parts: list[str] = []
    if response.filter_count is not None:
        meta_parts.append(f"{response.filter_count} candidates filtered")
    if response.llm_used:
        meta_parts.append("AI-ranked")
    else:
        meta_parts.append("Scorer-ranked")
    parts.append(" | ".join(meta_parts))

    if response.messages:
        for msg in response.messages:
            parts.append(f"Note: {msg}")

    return "\n\n".join(parts)

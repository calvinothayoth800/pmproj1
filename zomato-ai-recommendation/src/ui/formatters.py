"""Human-readable display helpers for the Streamlit UI."""

from __future__ import annotations

from src.phases.phase00.output_contract import RecommendationItem, RecommendationResponse


from typing import Optional


def format_cost(cost: Optional[int]) -> str:
    """Format INR cost for two with currency symbol."""
    if cost is None:
        return "Price not listed"
    return f"₹{cost:,}"


def format_rating(rating: Optional[float]) -> str:
    """Format rating with star symbol."""
    if rating is None:
        return "Rating N/A"
    return f"⭐ {rating:.1f}/5"


def format_cuisines(cuisine_str: str) -> list[str]:
    """Split pipe-separated cuisine string into displayable tags."""
    if not cuisine_str:
        return []
    return [t.strip().title() for t in cuisine_str.split("|") if t.strip()]


def format_dish_liked(dish_str: str) -> list[str]:
    """Split pipe-separated dish_liked into displayable tags."""
    if not dish_str:
        return []
    return [t.strip().title() for t in dish_str.split("|") if t.strip()]


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

    # Header line: rank + name
    lines.append(f"### {item.rank}. {item.name}")

    # Rating + cost line
    rating_str = format_rating(item.rating)
    cost_str = format_cost(item.estimated_cost)
    lines.append(f"{rating_str}  ·  {cost_str}")

    # Location
    if item.location:
        lines.append(f"📍 {item.location}")

    # Cuisine tags
    cuisines = format_cuisines(item.cuisine)
    if cuisines:
        lines.append(f"🍽️ {' · '.join(cuisines)}")

    # Popular dishes
    dishes = format_dish_liked(item.dish_liked)
    if dishes:
        lines.append(f"🔥 Popular: {', '.join(dishes[:6])}")

    # Badges
    badges: list[str] = []
    if item.online_order:
        badges.append("🛒 Order Online")
    if item.book_table:
        badges.append("🪑 Book Table")
    if item.votes > 0:
        badges.append(f"👤 {format_votes(item.votes)}")
    if badges:
        lines.append("  ".join(badges))

    # AI explanation
    if item.explanation:
        lines.append(f"\n> {item.explanation}")

    lines.append("---")
    return "\n".join(lines)


def response_summary_markdown(response: RecommendationResponse) -> str:
    """Build a summary block for the top of the results."""
    parts: list[str] = []

    if response.summary:
        parts.append(f"**Summary:** {response.summary}")

    meta_parts: list[str] = []
    if response.filter_count is not None:
        meta_parts.append(f"{response.filter_count} candidates filtered")
    if response.llm_used:
        meta_parts.append("AI-ranked ✨")
    else:
        meta_parts.append("Scorer-ranked (LLM offline)")
    parts.append(" · ".join(meta_parts))

    if response.messages:
        for msg in response.messages:
            parts.append(f"⚠️ {msg}")

    return "\n\n".join(parts)

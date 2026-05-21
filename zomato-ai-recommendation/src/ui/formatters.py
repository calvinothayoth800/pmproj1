"""Human-readable display helpers for the Streamlit UI."""

from __future__ import annotations

from html import escape
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
        return "N/A"
    return f"{rating:.1f}"


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


def _pill(label: str, variant: str = "") -> str:
    class_name = f"result-pill {variant}".strip()
    return f"<span class='{class_name}'>{escape(label)}</span>"


def item_card_markdown(item: RecommendationItem) -> str:
    """Build an HTML string for one recommendation card."""
    cuisines = format_cuisines(item.cuisine)
    dishes = format_dish_liked(item.dish_liked)

    pills: list[str] = []
    if item.online_order:
        pills.append(_pill("Online ordering", "accent"))
    if item.book_table:
        pills.append(_pill("Table booking", "accent"))
    if item.votes > 0:
        pills.append(_pill(format_votes(item.votes)))

    cuisine_text = ", ".join(cuisines[:5]) if cuisines else "Cuisine not listed"
    dish_html = ""
    if dishes:
        dish_html = (
            "<div class='result-dishes'>"
            f"<span>Popular</span>{escape(', '.join(dishes[:6]))}"
            "</div>"
        )

    explanation_html = ""
    if item.explanation:
        explanation_html = f"<p class='result-explanation'>{escape(item.explanation)}</p>"

    availability_html = ""
    if pills:
        availability_html = f"<div class='result-pills'>{''.join(pills)}</div>"

    return (
        '<article class="result-card">'
        f'<div class="result-rank">{item.rank:02d}</div>'
        '<div class="result-body">'
        '<div class="result-topline">'
        "<div>"
        f"<h3>{escape(item.name)}</h3>"
        f'<p class="result-location">{escape(item.location or "Location not listed")}</p>'
        "</div>"
        '<div class="result-score">'
        f"<strong>{escape(format_rating(item.rating))}</strong>"
        "<span>rating</span>"
        "</div>"
        "</div>"
        '<div class="result-meta">'
        f"<span>{escape(format_cost(item.estimated_cost))} for two</span>"
        f"<span>{escape(cuisine_text)}</span>"
        "</div>"
        f"{dish_html}"
        f"{availability_html}"
        f"{explanation_html}"
        "</div>"
        "</article>"
    )


def response_summary_markdown(response: RecommendationResponse) -> str:
    """Build an HTML summary block for the top of the results."""
    summary = escape(response.summary or "Here are the restaurants that best match your preferences.")
    count = response.filter_count if response.filter_count is not None else 0

    notes = ""
    if response.messages:
        joined = " ".join(response.messages)
        notes = f"<p class='summary-note'>{escape(joined)}</p>"

    return (
        '<section class="summary-card">'
        "<div>"
        '<span class="summary-kicker">Shortlist summary</span>'
        f"<p>{summary}</p>"
        "</div>"
        '<div class="summary-count">'
        f"<strong>{count}</strong>"
        "<span>candidates</span>"
        "</div>"
        f"{notes}"
        "</section>"
    )

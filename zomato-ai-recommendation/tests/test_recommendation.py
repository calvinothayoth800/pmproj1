"""Tests for Phase 03 — LLM recommendation."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
import httpx
import pandas as pd
import pytest

from src.phases.phase00.preferences import UserPreferences, PreferenceExtras
from src.phases.phase00.output_contract import RecommendationItem, RecommendationResponse
from src.llm.prompt_builder import SYSTEM_PROMPT, build_user_prompt
from src.llm.client import complete
from src.llm.parser import parse_llm_json, drop_unknown_names, enrich_from_dataframe
from src.services.recommendation_service import RecommendationService


# -----------------------------------------------------------------------------
# 1. Prompt Builder Tests
# -----------------------------------------------------------------------------
def test_prompt_builder_user_prompt() -> None:
    prefs = UserPreferences(
        city="Whitefield",
        budget="medium",
        cuisines=["North Indian"],
        min_rating=4.0,
        extras=PreferenceExtras(family_friendly=True, quick_service=False, book_table=True),
    )
    candidates = [
        {"name": "EAT.FIT", "cuisines": "north indian|biryani", "rating": 4.4, "cost_for_two": 500, "budget_tier": "medium", "location": "Whitefield"},
        {"name": "Faasos", "cuisines": "north indian|fast food", "rating": 4.0, "cost_for_two": 500, "budget_tier": "medium", "location": "Whitefield"},
    ]
    prompt = build_user_prompt(prefs, candidates, top_k=2)
    
    assert "Whitefield" in prompt
    assert "medium" in prompt
    assert "North Indian" in prompt
    assert "EAT.FIT" in prompt
    assert "Faasos" in prompt


# -----------------------------------------------------------------------------
# 2. Response Parser Tests
# -----------------------------------------------------------------------------
def test_parse_llm_json_clean() -> None:
    clean_json = '{"recommendations": [{"name": "A", "explanation": "Good"}], "summary": "Cool"}'
    parsed = parse_llm_json(clean_json)
    assert parsed["summary"] == "Cool"
    assert len(parsed["recommendations"]) == 1

def test_parse_llm_json_markdown() -> None:
    wrapped_json = """Some conversational text...
```json
{
  "recommendations": [{"name": "B", "explanation": "Fast"}],
  "summary": "Great"
}
```
More text..."""
    parsed = parse_llm_json(wrapped_json)
    assert parsed["summary"] == "Great"
    assert parsed["recommendations"][0]["name"] == "B"

def test_parse_llm_json_invalid() -> None:
    invalid = "Not JSON at all"
    with pytest.raises(ValueError, match="not valid JSON"):
        parse_llm_json(invalid)


# -----------------------------------------------------------------------------
# 3. Grounding / Validation Tests
# -----------------------------------------------------------------------------
def test_drop_unknown_names() -> None:
    candidates_df = pd.DataFrame([
        {"name": "Eat.Fit"},
        {"name": "Faasos"},
    ])
    recs = [
        {"name": "eat.fit", "explanation": "Fits perfectly"},
        {"name": "McDonalds", "explanation": "Hallucinated"}, # Hallucinated
        {"name": "Faasos", "explanation": "Also fits"},
    ]
    
    filtered = drop_unknown_names(recs, candidates_df)
    assert len(filtered) == 2
    assert {r["name"].lower() for r in filtered} == {"eat.fit", "faasos"}

def test_enrich_from_dataframe() -> None:
    candidates_df = pd.DataFrame([
        {"name": "Eat.Fit", "rating": 4.4, "cost_for_two": 500, "cuisines": "healthy|north indian", "location": "Koramangala", "dish_liked": "Salad|Bowl", "book_table": "Yes", "online_order": "No", "votes": 200},
        {"name": "Faasos", "rating": 4.0, "cost_for_two": 400, "cuisines": "fast food", "location": "HSR Layout", "dish_liked": "Wraps", "book_table": "No", "online_order": "Yes", "votes": 150},
    ])
    recs = [
        {"name": "EAT.FIT", "explanation": "Delicious & healthy"},
        {"name": "faasos", "explanation": "Quick roll"},
    ]

    enriched = enrich_from_dataframe(recs, candidates_df)
    assert len(enriched) == 2

    # Check that casing is restored to database ground truth
    assert enriched[0].name == "Eat.Fit"
    assert enriched[0].rating == 4.4
    assert enriched[0].estimated_cost == 500
    assert enriched[0].cuisine == "healthy|north indian"
    assert enriched[0].explanation == "Delicious & healthy"
    assert enriched[0].rank == 1
    assert enriched[0].location == "Koramangala"
    assert enriched[0].dish_liked == "Salad|Bowl"
    assert enriched[0].book_table is True
    assert enriched[0].online_order is False
    assert enriched[0].votes == 200

    assert enriched[1].name == "Faasos"
    assert enriched[1].rating == 4.0
    assert enriched[1].estimated_cost == 400
    assert enriched[1].cuisine == "fast food"
    assert enriched[1].explanation == "Quick roll"
    assert enriched[1].rank == 2
    assert enriched[1].location == "HSR Layout"
    assert enriched[1].dish_liked == "Wraps"
    assert enriched[1].book_table is False
    assert enriched[1].online_order is True
    assert enriched[1].votes == 150


# -----------------------------------------------------------------------------
# 4. LLM Client Retry Tests
# -----------------------------------------------------------------------------
@patch("httpx.Client.post")
@patch("src.llm.client.LLM_API_KEY", "gsk_test_key")
def test_client_complete_retry_on_429(mock_post: MagicMock) -> None:
    # First response: 429 Rate Limit
    # Second response: 200 Success
    response_429 = MagicMock()
    response_429.status_code = 429
    response_429.raise_for_status.side_effect = httpx.HTTPStatusError("429 Too Many Requests", request=MagicMock(), response=response_429)

    response_200 = MagicMock()
    response_200.status_code = 200
    response_200.json.return_value = {
        "choices": [{"message": {"content": '{"recommendations": [], "summary": "No candidates"}'}}]
    }

    mock_post.side_effect = [response_429, response_200]

    with patch("time.sleep") as mock_sleep:
        content = complete([{"role": "user", "content": "Hello"}])
        assert "No candidates" in content
        assert mock_post.call_count == 2
        mock_sleep.assert_called_once_with(1) # wait 2^0 = 1s


# -----------------------------------------------------------------------------
# 5. Recommendation Service Tests
# -----------------------------------------------------------------------------
def test_recommendation_service_empty_candidates() -> None:
    df = pd.DataFrame(
        columns=[
            "restaurant_id",
            "name",
            "city",
            "location",
            "cuisines",
            "rating",
            "votes",
            "cost_for_two",
            "budget_tier",
            "rest_type",
            "online_order",
            "book_table",
            "dish_liked",
            "listed_in_type",
        ]
    )
    service = RecommendationService(df)
    prefs = UserPreferences(city="Delhi", budget="medium", cuisines=[], min_rating=4.0)
    
    response = service.recommend(prefs)
    assert isinstance(response, RecommendationResponse)
    assert len(response.items) == 0
    assert response.llm_used is False
    assert any("No restaurant rows loaded" in m for m in response.messages)

@patch("src.services.recommendation_service.complete")
@patch("src.services.recommendation_service.LLM_API_KEY", "gsk_test_key")
def test_recommendation_service_success(mock_complete: MagicMock) -> None:
    # Prepare dummy candidate dataframe
    df = pd.DataFrame([
        {"restaurant_id": 1, "name": "Eat.Fit", "city": "Whitefield", "rating": 4.4, "cost_for_two": 500, "budget_tier": "medium", "cuisines": "healthy|north indian", "votes": 100, "location": "Whitefield", "rest_type": "casual dining", "online_order": "Yes", "book_table": "No", "dish_liked": "Salad"},
        {"restaurant_id": 2, "name": "Faasos", "city": "Whitefield", "rating": 4.0, "cost_for_two": 400, "budget_tier": "medium", "cuisines": "fast food", "votes": 150, "location": "Whitefield", "rest_type": "quick bites", "online_order": "Yes", "book_table": "No", "dish_liked": "Wraps"},
    ])

    mock_complete.return_value = json.dumps({
        "recommendations": [
            {"name": "Eat.Fit", "explanation": "Healthy choices."},
            {"name": "Faasos", "explanation": "Great rolls."}
        ],
        "summary": "Best medium budget in Whitefield."
    })

    service = RecommendationService(df)
    prefs = UserPreferences(city="Whitefield", budget="medium", cuisines=[], min_rating=4.0)

    response = service.recommend(prefs, top_k=2)
    assert response.llm_used is True
    assert len(response.items) == 2
    assert response.items[0].name == "Eat.Fit"
    assert response.items[0].explanation == "Healthy choices."
    assert response.items[0].location == "Whitefield"
    assert response.items[0].dish_liked == "Salad"
    assert response.items[0].book_table is False
    assert response.items[0].online_order is True
    assert response.items[0].votes == 100
    assert response.items[1].name == "Faasos"
    assert response.items[1].explanation == "Great rolls."
    assert response.items[1].location == "Whitefield"
    assert response.items[1].dish_liked == "Wraps"
    assert response.items[1].book_table is False
    assert response.items[1].online_order is True
    assert response.items[1].votes == 150
    assert response.summary == "Best medium budget in Whitefield."

@patch("src.services.recommendation_service.complete")
@patch("src.services.recommendation_service.LLM_API_KEY", "gsk_test_key")
def test_recommendation_service_fallback_on_llm_failure(mock_complete: MagicMock) -> None:
    df = pd.DataFrame([
        {"restaurant_id": 1, "name": "Eat.Fit", "city": "Whitefield", "rating": 4.4, "cost_for_two": 500, "budget_tier": "medium", "cuisines": "healthy|north indian", "votes": 200, "location": "Whitefield", "rest_type": "casual dining", "online_order": "Yes", "book_table": "No", "dish_liked": "Salad"},
    ])

    mock_complete.side_effect = RuntimeError("API rate limit exceeded")

    service = RecommendationService(df)
    prefs = UserPreferences(city="Whitefield", budget="medium", cuisines=[], min_rating=4.0)

    response = service.recommend(prefs, top_k=1)

    assert response.llm_used is False
    assert len(response.items) == 1
    assert response.items[0].name == "Eat.Fit"
    assert "LLM offline" in response.items[0].explanation
    assert any("AI recommendation failed" in msg for msg in response.messages)
    # Verify enriched fields from fallback path
    assert response.items[0].location == "Whitefield"
    assert response.items[0].dish_liked == "Salad"
    assert response.items[0].book_table is False
    assert response.items[0].online_order is True
    assert response.items[0].votes == 200

@patch("src.services.recommendation_service.complete")
@patch("src.services.recommendation_service.LLM_API_KEY", "gsk_test_key")
def test_recommendation_service_padding(mock_complete: MagicMock) -> None:
    # 2 candidates available, LLM only recommends 1 valid name. Service should pad to 2.
    df = pd.DataFrame([
        {"restaurant_id": 1, "name": "Eat.Fit", "city": "Whitefield", "rating": 4.4, "cost_for_two": 500, "budget_tier": "medium", "cuisines": "healthy", "votes": 100, "location": "Whitefield", "rest_type": "casual dining", "online_order": "Yes", "book_table": "No", "dish_liked": "Salad"},
        {"restaurant_id": 2, "name": "Faasos", "city": "Whitefield", "rating": 4.0, "cost_for_two": 400, "budget_tier": "medium", "cuisines": "fast food", "votes": 150, "location": "Whitefield", "rest_type": "quick bites", "online_order": "Yes", "book_table": "No", "dish_liked": "Wraps"},
    ])
    
    mock_complete.return_value = json.dumps({
        "recommendations": [
            {"name": "Eat.Fit", "explanation": "Healthy choices."},
            {"name": "McDonalds", "explanation": "Hallucinated name."} # Should be dropped & padded by Faasos
        ],
        "summary": "Whitefield options."
    })

    service = RecommendationService(df)
    prefs = UserPreferences(city="Whitefield", budget="medium", cuisines=[], min_rating=4.0)
    
    response = service.recommend(prefs, top_k=2)
    assert response.llm_used is True
    assert len(response.items) == 2
    assert response.items[0].name == "Eat.Fit"
    assert response.items[0].explanation == "Healthy choices."
    assert response.items[1].name == "Faasos"
    assert "LLM fallback explanation" in response.items[1].explanation

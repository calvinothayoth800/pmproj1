"""HTTP LLM client using httpx with exponential backoff retries."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional
import httpx

from src.config import LLM_BASE_URL, LLM_MODEL, get_llm_api_key

logger = logging.getLogger(__name__)

def complete(
    messages: list[dict[str, str]],
    response_format: Optional[dict[str, str]] = None,
    timeout_seconds: float = 30.0,
    max_retries: int = 3,
) -> str:
    """
    Perform a chat completion request to the configured LLM API (Groq/OpenAI compatible).

    Args:
        messages: List of chat messages (e.g. system and user prompts).
        response_format: Optional dict (e.g. {"type": "json_object"}).
        timeout_seconds: Request timeout.
        max_retries: Number of backoff retries for 429/5xx or timeout errors.

    Returns:
        The content string returned by the LLM.

    Raises:
        ValueError: If LLM_API_KEY is not configured.
        RuntimeError: If all retry attempts fail.
    """
    llm_api_key = get_llm_api_key()
    if not llm_api_key:
        raise ValueError("LLM API key is not configured. Please set GROQ_API_KEY in .env.")

    url = f"{LLM_BASE_URL.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {llm_api_key}",
        "Content-Type": "application/json",
    }

    payload: dict[str, Any] = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": 0.2,
    }
    if response_format is not None:
        payload["response_format"] = response_format

    last_err: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            logger.info("Calling LLM API: model=%s URL=%s (attempt %s/%s)", LLM_MODEL, url, attempt + 1, max_retries)
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(url, json=payload, headers=headers)

                # Check if it succeeded
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if not choices:
                        raise ValueError(f"Empty choices in API response: {data}")
                    content = choices[0].get("message", {}).get("content", "")
                    return content

                # Handle failure status codes
                if response.status_code == 429:
                    logger.warning("LLM API rate limited (429).")
                    response.raise_for_status()
                elif response.status_code >= 500:
                    logger.warning("LLM API server error (%s).", response.status_code)
                    response.raise_for_status()
                else:
                    # Unrecoverable error (e.g. 400, 401, 403, 404), do not retry
                    logger.error("LLM API unrecoverable error (%s): %s", response.status_code, response.text)
                    response.raise_for_status()

        except (httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as exc:
            last_err = exc
            # If it's a 400-range error other than 429, don't retry
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"Unrecoverable LLM API error: {exc}") from exc

            wait_time = 2 ** attempt
            logger.warning("LLM API call failed: %s; retrying in %ss...", exc, wait_time)
            time.sleep(wait_time)

    # Propagate failure if all retries exhausted
    raise RuntimeError(f"Failed to query LLM API after {max_retries} attempts.") from last_err

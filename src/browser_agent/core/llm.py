"""LLM integration for the browser agent.

This module provides LLM client setup for OpenRouter API integration.
"""

import os
from typing import Any

from openai import AsyncOpenAI, OpenAI

from agents import set_default_openai_client
from agents.models.openai_provider import OpenAIProvider

from browser_agent.core.logging import ErrorIds, logError

# Default model to use on OpenRouter
DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"

# Default model for OpenAI Agents SDK usage
DEFAULT_SDK_MODEL = "google/gemini-2.5-flash"


def setup_openrouter_for_sdk() -> OpenAIProvider:
    """Configure the OpenAI Agents SDK to use OpenRouter as the LLM backend.

    Creates an AsyncOpenAI client pointed at OpenRouter's OpenAI-compatible API,
    sets it as the SDK default, and returns an OpenAIProvider that bypasses
    the SDK's MultiProvider prefix parsing (which would strip the provider
    prefix from model names like 'google/gemini-...' that OpenRouter needs).

    Returns:
        An OpenAIProvider configured for OpenRouter with chat completions mode.

    Raises:
        ValueError: If OPENROUTER_API_KEY is not set.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable must be set. "
            "Get one at https://openrouter.ai/keys"
        )

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    set_default_openai_client(client)
    return OpenAIProvider(openai_client=client, use_responses=False)


def get_openrouter_client() -> OpenAI:
    """Get an OpenAI client configured for OpenRouter.

    The OPENROUTER_API_KEY environment variable must be set.

    Returns:
        An OpenAI client instance configured for OpenRouter.

    Raises:
        ValueError: If OPENROUTER_API_KEY is not set.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable must be set. "
            "Get one at https://openrouter.ai/keys"
        )

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def call_llm(
    messages: list[dict[str, Any]],  # type: ignore[arg-type]
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> str:
    """Call the LLM with the given messages.

    Args:
        messages: List of message dictionaries with 'role' and 'content' keys.
        model: Model name to use. If None, uses DEFAULT_MODEL.
        temperature: Sampling temperature (0-2).
        max_tokens: Maximum tokens to generate.

    Returns:
        The LLM's response text.

    """
    if model is None:
        model = DEFAULT_MODEL

    client = get_openrouter_client()

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as e:
        logError(ErrorIds.LLM_API_ERROR, f"LLM API call failed: {e}", exc_info=True)
        raise

    if not response.choices:
        logError(ErrorIds.LLM_MALFORMED_RESPONSE, "LLM returned empty choices list")
        return ""
    return response.choices[0].message.content or ""

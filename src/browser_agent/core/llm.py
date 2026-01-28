"""LLM integration for the browser agent.

This module provides LLM client setup for OpenRouter API integration.
"""

import os
from typing import Any

from openai import AsyncOpenAI, OpenAI, OpenAIError

from agents import set_default_openai_client

# Default model to use on OpenRouter
DEFAULT_MODEL = "anthropic/claude-3.5-sonnet"

# Default model for OpenAI Agents SDK usage
DEFAULT_SDK_MODEL = "google/gemini-2.5-flash-preview-05-20"


def setup_openrouter_for_sdk() -> None:
    """Configure the OpenAI Agents SDK to use OpenRouter as the LLM backend.

    Sets the default AsyncOpenAI client for the SDK, pointed at OpenRouter's
    OpenAI-compatible API. The OPENROUTER_API_KEY environment variable must be set.

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

    Raises:
        OpenAIError: If the API call fails.
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
        return response.choices[0].message.content or ""
    except OpenAIError as e:
        raise

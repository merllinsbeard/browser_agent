"""Browser Agent core components."""

from browser_agent.core.browser import launch_persistent_context
from browser_agent.core.llm import DEFAULT_MODEL, call_llm, get_openrouter_client
from browser_agent.core.registry import ElementRegistry, StaleElementError
from browser_agent.core.recovery import (
    RetryAttempt,
    RetryResult,
    detect_and_handle_overlays,
    needs_reobservation,
    retry_with_backoff,
)

__all__ = [
    "launch_persistent_context",
    "get_openrouter_client",
    "call_llm",
    "DEFAULT_MODEL",
    "ElementRegistry",
    "StaleElementError",
    "detect_and_handle_overlays",
    "needs_reobservation",
    "retry_with_backoff",
    "RetryAttempt",
    "RetryResult",
]

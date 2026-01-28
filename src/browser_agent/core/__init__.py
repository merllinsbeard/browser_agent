"""Browser Agent core components."""

from browser_agent.core.browser import (
    launch_persistent_context,
    launch_persistent_context_async,
)
from browser_agent.core.context import ContextTracker
from browser_agent.core.logging import ErrorIds, logError, logEvent, logForDebugging
from browser_agent.core.llm import (
    DEFAULT_MODEL,
    DEFAULT_SDK_MODEL,
    call_llm,
    get_openrouter_client,
    setup_openrouter_for_sdk,
)
from browser_agent.core.registry import ElementRegistry, StaleElementError

__all__ = [
    "launch_persistent_context",
    "launch_persistent_context_async",
    "get_openrouter_client",
    "call_llm",
    "DEFAULT_MODEL",
    "DEFAULT_SDK_MODEL",
    "setup_openrouter_for_sdk",
    "ElementRegistry",
    "StaleElementError",
    "ContextTracker",
    "logError",
    "logForDebugging",
    "logEvent",
    "ErrorIds",
]

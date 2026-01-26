"""Logging infrastructure for browser agent.

This module provides structured logging for errors, debugging, and analytics.
All logging functions use the standard library logging module for flexibility.
"""

import logging
import sys
from typing import Any

# Error ID constants for tracking and Sentry integration
class ErrorIds:
    """Constants for error IDs used in logging and error tracking."""

    # Element registry errors
    STALE_ELEMENT_REFERENCE = "ERR_STALE_ELEMENT"
    ELEMENT_NOT_FOUND = "ERR_ELEMENT_NOT_FOUND"
    REGISTRY_VERSION_MISMATCH = "ERR_REGISTRY_VERSION"

    # Page observation errors
    ARIA_SNAPSHOT_PARSE_FAILED = "ERR_ARIA_PARSE"
    VISIBLE_TEXT_EXTRACTION_FAILED = "ERR_TEXT_EXTRACT"
    SCREENSHOT_CAPTURE_FAILED = "ERR_SCREENSHOT"

    # Action execution errors
    CLICK_TIMEOUT = "ERR_CLICK_TIMEOUT"
    TYPE_TIMEOUT = "ERR_TYPE_TIMEOUT"
    NAVIGATION_FAILED = "ERR_NAVIGATE"
    ELEMENT_INTERACTION_FAILED = "ERR_ELEMENT_INTERACT"

    # Recovery/overlay errors
    OVERLAY_DISMISS_FAILED = "ERR_OVERLAY_DISMISS"
    OVERLAY_DETECTION_FAILED = "ERR_OVERLAY_DETECT"
    RETRY_EXHAUSTED = "ERR_RETRY_EXHAUSTED"

    # LLM/API errors
    LLM_API_ERROR = "ERR_LLM_API"
    LLM_RATE_LIMIT = "ERR_LLM_RATE_LIMIT"
    LLM_TIMEOUT = "ERR_LLM_TIMEOUT"
    LLM_MALFORMED_RESPONSE = "ERR_LLM_MALFORMED"

    # General errors
    UNEXPECTED_ERROR = "ERR_UNEXPECTED"
    KEYBOARD_INTERRUPT = "KEYBOARD_INTERRUPT"


# Configure root logger for the browser agent
_logger: logging.Logger | None = None


def _get_logger() -> logging.Logger:
    """Get or create the logger instance."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger("browser_agent")
        _logger.setLevel(logging.DEBUG)

        # Console handler for user-facing logs
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(console_formatter)
        _logger.addHandler(console_handler)

    return _logger


def logError(
    error_id: str,
    message: str,
    exc_info: bool = False,
    extra: dict[str, Any] | None = None,
) -> None:
    """Log an error for error tracking (e.g., Sentry).

    Args:
        error_id: The error ID constant from ErrorIds.
        message: Human-readable error message.
        exc_info: If True, include exception info in the log.
        extra: Optional additional context as key-value pairs.
    """
    logger = _get_logger()
    log_msg = f"[{error_id}] {message}"
    if extra:
        extra_str = ", ".join(f"{k}={v}" for k, v in extra.items())
        log_msg += f" | {extra_str}"

    logger.error(log_msg, exc_info=exc_info)

    # In production, this would also send to Sentry/error tracking service
    # Example: sentry_sdk.capture_exception(error_id, message, extra)


def logForDebugging(
    message: str,
    level: str = "debug",
    extra: dict[str, Any] | None = None,
) -> None:
    """Log a user-facing debug message.

    Args:
        message: The message to log.
        level: Log level - "debug", "info", "warning", or "error".
        extra: Optional additional context as key-value pairs.
    """
    logger = _get_logger()
    log_msg = message
    if extra:
        extra_str = ", ".join(f"{k}={v}" for k, v in extra.items())
        log_msg += f" | {extra_str}"

    log_level = getattr(logging, level.upper(), logging.DEBUG)
    logger.log(log_level, log_msg)


def logEvent(
    event_name: str,
    properties: dict[str, Any] | None = None,
) -> None:
    """Log an analytics event.

    Args:
        event_name: The name of the event (e.g., "action_executed", "overlay_dismissed").
        properties: Optional event properties as key-value pairs.
    """
    logger = _get_logger()
    log_msg = f"[EVENT] {event_name}"
    if properties:
        props_str = ", ".join(f"{k}={v}" for k, v in properties.items())
        log_msg += f" | {props_str}"

    logger.info(log_msg)

    # In production, this would also send to analytics service
    # Example: analytics.track(event_name, properties)


def set_log_level(level: str | int) -> None:
    """Set the logging level for the browser agent.

    Args:
        level: Log level as string ("debug", "info", "warning", "error")
               or int (logging.DEBUG, logging.INFO, etc.).
    """
    logger = _get_logger()
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(level)
    logger.handlers[0].setLevel(level)


def enable_file_logging(filepath: str) -> None:
    """Enable file logging to a specific file.

    Args:
        filepath: Path to the log file.
    """
    logger = _get_logger()
    file_handler = logging.FileHandler(filepath)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

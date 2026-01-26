"""Type action tool for browser automation.

This module provides the type_ function for typing text into
input elements by their reference ID.
"""

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from browser_agent.core.registry import ElementRegistry, StaleElementError
from browser_agent.models.result import ActionResult


def type_(
    page: Page,
    registry: ElementRegistry,
    element_id: str,
    text: str,
    timeout: float = 30000,
) -> ActionResult:
    """Type text into an input element by its reference ID.

    Args:
        page: The Playwright Page object.
        registry: The ElementRegistry for resolving element references.
        element_id: The reference ID of the input element.
        text: The text to type into the element.
        timeout: Maximum time to wait for type to complete (ms). Default: 30000.

    Returns:
        ActionResult indicating success or failure with a descriptive message.
    """
    try:
        # Get the locator for the element
        locator = registry.get_locator(page, element_id)

        # Fill the element with text
        locator.fill(text, timeout=timeout)

        return ActionResult.success_result(
            message=f"Successfully typed text into element {element_id!r}"
        )

    except StaleElementError as e:
        return ActionResult.failure_result(
            message=f"Failed to type into element {element_id!r}: stale element reference",
            error=str(e),
        )

    except PlaywrightTimeoutError as e:
        return ActionResult.failure_result(
            message=f"Timeout typing into element {element_id!r}",
            error=str(e),
        )

    except Exception as e:
        return ActionResult.failure_result(
            message=f"Failed to type into element {element_id!r}",
            error=str(e),
        )

"""Click action tool for browser automation.

This module provides the click function for clicking interactive
elements by their reference ID.
"""

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from browser_agent.core.registry import ElementRegistry, StaleElementError
from browser_agent.models.result import ActionResult, failure_result, success_result


def click(
    page: Page,
    registry: ElementRegistry,
    element_id: str,
    timeout: float = 30000,
) -> ActionResult:
    """Click an interactive element by its reference ID.

    Args:
        page: The Playwright Page object.
        registry: The ElementRegistry for resolving element references.
        element_id: The reference ID of the element to click.
        timeout: Maximum time to wait for click to complete (ms). Default: 30000.

    Returns:
        ActionResult indicating success or failure with a descriptive message.
    """
    try:
        # Get the locator for the element
        locator = registry.get_locator(page, element_id)

        # Perform the click
        locator.click(timeout=timeout)

        return success_result(
            message=f"Successfully clicked element {element_id!r}"
        )

    except StaleElementError as e:
        return failure_result(
            message=f"Failed to click element {element_id!r}: stale element reference",
            error=str(e),
        )

    except PlaywrightTimeoutError as e:
        return failure_result(
            message=f"Timeout clicking element {element_id!r}",
            error=str(e),
        )

    except Exception as e:
        return failure_result(
            message=f"Failed to click element {element_id!r}",
            error=str(e),
        )

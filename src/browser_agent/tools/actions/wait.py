"""Wait action tool for browser automation.

This module provides the wait function for waiting for conditions or timeouts.
"""

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from browser_agent.models.result import ActionResult, failure_result, success_result


def wait(page: Page, timeout: float = 1000) -> ActionResult:
    """Wait for a specified timeout.

    Args:
        page: The Playwright Page object.
        timeout: Time to wait in milliseconds. Default: 1000.

    Returns:
        ActionResult indicating success or failure with a descriptive message.

    Note:
        This function waits for a fixed timeout. For waiting for specific
        conditions (e.g., element visibility, URL change), use Playwright's
        wait_for_* methods directly.
    """
    try:
        page.wait_for_timeout(timeout)

        return success_result(
            message=f"Successfully waited {timeout}ms"
        )

    except Exception as e:
        return failure_result(
            message=f"Failed to wait {timeout}ms",
            error=str(e),
        )

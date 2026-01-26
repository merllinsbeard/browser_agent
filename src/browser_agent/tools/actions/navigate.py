"""Navigate action tool for browser automation.

This module provides the navigate function for navigating to URLs.
"""

from typing import Literal

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from browser_agent.models.result import ActionResult

WaitUntil = Literal["commit", "domcontentloaded", "load", "networkidle"]


def navigate(
    page: Page,
    url: str,
    wait_until: WaitUntil = "load",
    timeout: float = 30000,
) -> ActionResult:
    """Navigate to a URL.

    Args:
        page: The Playwright Page object.
        url: The URL to navigate to.
        wait_until: When to consider navigation succeeded.
                  Options: "load", "domcontentloaded", "networkidle". Default: "load".
        timeout: Maximum time to wait for navigation (ms). Default: 30000.

    Returns:
        ActionResult indicating success or failure with a descriptive message.
    """
    try:
        response = page.goto(url, wait_until=wait_until, timeout=timeout)

        if response is None:
            # Navigation succeeded but no response received (e.g., for non-http protocols)
            return ActionResult.success_result(
                message=f"Successfully navigated to {url!r}"
            )

        status = response.status
        if 200 <= status < 400:
            return ActionResult.success_result(
                message=f"Successfully navigated to {url!r} (status: {status})"
            )
        else:
            return ActionResult.failure_result(
                message=f"Navigation to {url!r} returned status {status}",
                error=f"HTTP {status}",
            )

    except PlaywrightTimeoutError as e:
        return ActionResult.failure_result(
            message=f"Timeout navigating to {url!r}",
            error=str(e),
        )

    except Exception as e:
        return ActionResult.failure_result(
            message=f"Failed to navigate to {url!r}",
            error=str(e),
        )

"""Scroll action tool for browser automation.

This module provides the scroll function for scrolling the page.
"""

from playwright.sync_api import Page

from browser_agent.models.result import ActionResult


def scroll(page: Page, dx: int = 0, dy: int = 0) -> ActionResult:
    """Scroll the page by the specified delta.

    Args:
        page: The Playwright Page object.
        dx: Horizontal scroll delta in pixels (positive = right, negative = left).
        dy: Vertical scroll delta in pixels (positive = down, negative = up).

    Returns:
        ActionResult indicating success or failure with a descriptive message.

    Note:
        This function uses JavaScript's scrollBy() to scroll the page.
        For scrolling to a specific element, use the locator's scroll_into_view()
        method instead.
    """
    try:
        if dx == 0 and dy == 0:
            return ActionResult.success_result(
                message="No scroll performed (dx=0, dy=0)"
            )

        page.evaluate(f"window.scrollBy({dx}, {dy})")

        direction_parts = []
        if dx != 0:
            direction_parts.append(f"{'right' if dx > 0 else 'left'} {abs(dx)}px")
        if dy != 0:
            direction_parts.append(f"{'down' if dy > 0 else 'up'} {abs(dy)}px")

        return ActionResult.success_result(
            message=f"Successfully scrolled {' and '.join(direction_parts)}"
        )

    except Exception as e:
        return ActionResult.failure_result(
            message=f"Failed to scroll page",
            error=str(e),
        )

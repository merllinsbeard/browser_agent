"""Press action tool for browser automation.

This module provides the press function for pressing keyboard keys.
"""

from playwright.sync_api import Page

from browser_agent.models.result import ActionResult


def press(page: Page, key: str) -> ActionResult:
    """Press a keyboard key.

    Args:
        page: The Playwright Page object.
        key: The key to press (e.g., "Enter", "Escape", "F1", "ArrowDown").

    Returns:
        ActionResult indicating success or failure with a descriptive message.

    Note:
        Key names follow the Playwright/KeyboardEvent standard:
        - Modifier keys: "Shift", "Control", "Alt", "Meta"
        - Special keys: "Enter", "Escape", "Backspace", "Tab", "Delete"
        - Arrow keys: "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"
        - Function keys: "F1" through "F12"
        - For key combinations, use + separator: "Control+A"
    """
    try:
        page.keyboard.press(key)

        return ActionResult.success_result(
            message=f"Successfully pressed key {key!r}"
        )

    except Exception as e:
        return ActionResult.failure_result(
            message=f"Failed to press key {key!r}",
            error=str(e),
        )

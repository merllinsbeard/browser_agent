"""Error recovery module for browser automation.

This module provides recovery strategies for handling failures during
browser automation, including overlay detection and dismissal.
"""

from playwright.sync_api import Page

from browser_agent.models.element import InteractiveElement
from browser_agent.models.result import ActionResult
from browser_agent.models.snapshot import PageSnapshot


def detect_and_handle_overlays(
    page: Page,
    snapshot: PageSnapshot,
) -> tuple[bool, str]:
    """Detect and handle modal overlays/popups that may block actions.

    Args:
        page: The Playwright Page object.
        snapshot: The current page snapshot to analyze for overlays.

    Returns:
        A tuple of (overlays_found, dismissal_result):
        - overlays_found: True if overlays were detected
        - dismissal_result: Description of what was done
    """
    # Look for dialog elements in the snapshot's interactive elements
    dialogs = [
        elem
        for elem in snapshot.interactive_elements
        if elem.role == "dialog" or elem.name.lower() in ("modal", "popup", "dialog")
    ]

    # Also check for aria-modal attribute in element descriptions
    aria_modals = [
        elem
        for elem in snapshot.interactive_elements
        if elem.aria_label and "modal" in elem.aria_label.lower()
    ]

    all_overlays = dialogs + aria_modals

    if not all_overlays:
        return False, "No overlays detected"

    # Try to dismiss each overlay
    dismissed_count = 0
    failed_dismissals = []

    for overlay in all_overlays:
        # Try common dismissal strategies in order
        dismissed = False

        # Strategy 1: Look for close button (X) in the overlay
        if not dismissed:
            dismissed = _try_dismiss_with_close_button(page, overlay)

        # Strategy 2: Look for Cancel/Close/No buttons
        if not dismissed:
            dismissed = _try_dismiss_with_cancel_button(page, overlay)

        # Strategy 3: Try Escape key
        if not dismissed:
            dismissed = _try_dismiss_with_escape(page)

        if dismissed:
            dismissed_count += 1
        else:
            failed_dismissals.append(overlay.ref)

    if dismissed_count > 0:
        result_msg = f"Dismissed {dismissed_count} of {len(all_overlays)} overlay(s)"
        if failed_dismissals:
            result_msg += f" (failed: {', '.join(failed_dismissals)})"
        return True, result_msg

    return True, f"Found {len(all_overlays)} overlay(s) but could not dismiss any"


def _try_dismiss_with_close_button(page: Page, overlay: InteractiveElement) -> bool:
    """Try to dismiss overlay by clicking a close button (X).

    Args:
        page: The Playwright Page object.
        overlay: The overlay element to dismiss.

    Returns:
        True if dismissal was attempted, False otherwise.
    """
    try:
        # Look for buttons with close/X patterns near the dialog
        close_patterns = ["×", "x", "close", "✕"]

        # Try to find close buttons within the dialog
        for pattern in close_patterns:
            try:
                # Look for buttons or links with the close pattern
                selectors = [
                    f'button:has-text("{pattern}")',
                    f'a[role="button"]:has-text("{pattern}")',
                    f'[aria-label*="close" i], [aria-label*="×" i]',
                ]

                for selector in selectors:
                    try:
                        locator = page.locator(selector).first
                        if locator.count() > 0:
                            locator.click(timeout=2000)
                            return True
                    except Exception:
                        continue
            except Exception:
                continue

    except Exception:
        pass

    return False


def _try_dismiss_with_cancel_button(page: Page, overlay: InteractiveElement) -> bool:
    """Try to dismiss overlay by clicking Cancel/Close/No button.

    Args:
        page: The Playwright Page object.
        overlay: The overlay element to dismiss.

    Returns:
        True if dismissal was attempted, False otherwise.
    """
    try:
        cancel_patterns = ["cancel", "close", "no", "dismiss", "not now", "later"]

        for pattern in cancel_patterns:
            try:
                selector = f'button:has-text("{pattern}")'
                locator = page.locator(selector).first
                if locator.count() > 0:
                    locator.click(timeout=2000)
                    return True
            except Exception:
                continue

    except Exception:
        pass

    return False


def _try_dismiss_with_escape(page: Page) -> bool:
    """Try to dismiss overlay by pressing Escape key.

    Args:
        page: The Playwright Page object.

    Returns:
        True if Escape was pressed, False otherwise.
    """
    try:
        page.keyboard.press("Escape")
        return True
    except Exception:
        return False


def needs_reobservation(action_result: "ActionResult") -> bool:
    """Check if an action failure requires page re-observation.

    Args:
        action_result: The result of the failed action.

    Returns:
        True if re-observation is recommended.
    """
    if action_result.success:
        return False

    # Re-observe if the error suggests the page state changed
    error = action_result.error or ""
    message = action_result.message or ""

    # Patterns that suggest the page changed unexpectedly
    reobserve_patterns = [
        "detached",
        "not found",
        "timeout",
        "element not found",
        "stale",
        "unexpected",
    ]

    error_lower = error.lower() + " " + message.lower()
    return any(pattern in error_lower for pattern in reobserve_patterns)

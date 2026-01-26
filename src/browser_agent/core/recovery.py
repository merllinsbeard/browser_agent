"""Error recovery module for browser automation.

This module provides recovery strategies for handling failures during
browser automation, including overlay detection and dismissal.

Follows CLAUDE.md constraints:
- NO hardcoded selectors
- Uses element registry pattern for all element interactions
- Runtime page text only as observed data
"""

import time
from typing import Callable

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from browser_agent.core.logging import ErrorIds, logError, logEvent, logForDebugging
from browser_agent.core.registry import ElementRegistry
from browser_agent.models.element import InteractiveElement
from browser_agent.models.result import ActionResult, failure_result
from browser_agent.models.snapshot import PageSnapshot


def _find_dismissal_elements(snapshot: PageSnapshot) -> dict[str, list[InteractiveElement]]:
    """Find close/cancel buttons from the page snapshot.

    Uses ONLY runtime-observed data from the snapshot, following CLAUDE.md rules.

    Args:
        snapshot: The current page snapshot to analyze for dismissal elements.

    Returns:
        A dict mapping dismissal type to list of matching elements:
        - "close": Close/X buttons
        - "cancel": Cancel/Close/No buttons
    """
    result: dict[str, list[InteractiveElement]] = {"close": [], "cancel": []}

    for elem in snapshot.interactive_elements:
        # Check if this element is a button or link
        if elem.role not in ("button", "link"):
            continue

        # Build text to search from runtime-observed attributes
        text_to_search = (
            (elem.name or "").lower() +
            " " +
            (elem.aria_label or "").lower() +
            " " +
            (elem.placeholder or "").lower()
        )

        # Close button patterns (X, close, etc.)
        close_patterns = ["×", "x", "close", "✕"]
        if any(pattern in text_to_search for pattern in close_patterns):
            result["close"].append(elem)

        # Cancel button patterns
        cancel_patterns = ["cancel", "close", "no", "dismiss", "not now", "later"]
        if any(pattern in text_to_search for pattern in cancel_patterns):
            result["cancel"].append(elem)

    logForDebugging(
        f"Found {len(result['close'])} close buttons, {len(result['cancel'])} cancel buttons"
    )
    return result


def detect_and_handle_overlays(
    page: Page,
    snapshot: PageSnapshot,
    registry: ElementRegistry,
) -> tuple[bool, str]:
    """Detect and handle modal overlays/popups using element registry pattern.

    NO hardcoded selectors - uses only runtime-observed data from snapshot.

    Args:
        page: The Playwright Page object.
        snapshot: The current page snapshot to analyze for overlays.
        registry: The ElementRegistry for getting element locators.

    Returns:
        A tuple of (overlays_found, dismissal_result):
        - overlays_found: True if overlays were detected
        - dismissal_result: Description of what was done
    """
    # Look for dialog elements in the snapshot's interactive elements
    # Uses runtime data only - no hardcoded patterns
    dialogs = [
        elem
        for elem in snapshot.interactive_elements
        if elem.role == "dialog" or elem.name.lower() in ("modal", "popup", "dialog")
    ]

    # Check for aria-modal attribute in runtime-observed data
    aria_modals = [
        elem
        for elem in snapshot.interactive_elements
        if elem.aria_label and "modal" in elem.aria_label.lower()
    ]

    all_overlays = dialogs + aria_modals

    if not all_overlays:
        return False, "No overlays detected"

    logEvent(
        "overlays_detected",
        {"count": len(all_overlays)}
    )

    # Find dismissal buttons from the snapshot
    dismissal_elements = _find_dismissal_elements(snapshot)

    # Try to dismiss each overlay using element registry
    dismissed_count = 0
    failed_dismissals = []

    for overlay in all_overlays:
        # Try common dismissal strategies in order
        dismissed = False

        # Strategy 1: Try close buttons via element registry
        if not dismissed and dismissal_elements["close"]:
            dismissed = _try_dismiss_with_elements(
                page, dismissal_elements["close"], registry
            )

        # Strategy 2: Try cancel buttons via element registry
        if not dismissed and dismissal_elements["cancel"]:
            dismissed = _try_dismiss_with_elements(
                page, dismissal_elements["cancel"], registry
            )

        # Strategy 3: Try Escape key (no selector needed)
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
        logEvent("overlays_dismissed", {"dismissed": dismissed_count, "total": len(all_overlays)})
        return True, result_msg

    logError(
        ErrorIds.OVERLAY_DISMISS_FAILED,
        f"Could not dismiss {len(all_overlays)} overlay(s)"
    )
    return True, f"Found {len(all_overlays)} overlay(s) but could not dismiss any"


def _try_dismiss_with_elements(
    page: Page,
    elements: list[InteractiveElement],
    registry: ElementRegistry,
) -> bool:
    """Try to dismiss overlay by clicking elements via element registry.

    Args:
        page: The Playwright Page object.
        elements: List of elements to try clicking.
        registry: The ElementRegistry for getting locators.

    Returns:
        True if any click was successful, False otherwise.
    """
    for elem in elements:
        try:
            locator = registry.get_locator(page, elem.ref)
            locator.click(timeout=2000)
            logEvent("overlay_dismissed_via_element", {"element_ref": elem.ref})
            return True
        except PlaywrightTimeoutError:
            logForDebugging(
                f"Timeout clicking {elem.ref}",
                level="debug"
            )
            continue
        except Exception as e:
            logError(
                ErrorIds.OVERLAY_DISMISS_FAILED,
                f"Error clicking {elem.ref}",
                exc_info=False
            )
            continue

    return False


def _try_dismiss_with_escape(page: Page) -> bool:
    """Try to dismiss overlay by pressing Escape key.

    Args:
        page: The Playwright Page object.

    Returns:
        True if Escape was pressed successfully.
    """
    try:
        page.keyboard.press("Escape")
        logEvent("overlay_dismissed_via_escape")
        return True
    except Exception as e:
        logError(
            ErrorIds.OVERLAY_DISMISS_FAILED,
            "Error pressing Escape",
            exc_info=False
        )
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


class RetryAttempt:
    """Represents a single retry attempt with its strategy."""

    def __init__(self, strategy: str, description: str) -> None:
        """Initialize a retry attempt.

        Args:
            strategy: The strategy name (e.g., "reobserve", "wait", "variant").
            description: Human-readable description of what was tried.
        """
        self.strategy = strategy
        self.description = description

    def __repr__(self) -> str:
        return f"RetryAttempt({self.strategy}: {self.description})"


class RetryResult:
    """Result of a retry operation."""

    def __init__(
        self,
        success: bool,
        final_result: ActionResult,
        attempts_made: list[RetryAttempt],
        should_ask_user: bool = False,
    ) -> None:
        """Initialize a retry result.

        Args:
            success: True if any retry attempt succeeded.
            final_result: The final ActionResult (success or last failure).
            attempts_made: List of retry attempts that were tried.
            should_ask_user: True if user should be asked for guidance.
        """
        self.success = success
        self.final_result = final_result
        self.attempts_made = attempts_made
        self.should_ask_user = should_ask_user


def retry_with_backoff(
    page: Page,
    initial_result: ActionResult,
    action_func: Callable[[], ActionResult],
    registry: ElementRegistry,
    max_attempts: int = 3,
    initial_backoff: float = 1.0,
) -> RetryResult:
    """Retry a failed action with exponential backoff and different strategies.

    Never retries the exact same action twice - each attempt uses a different
    recovery strategy (re-observation, wait, overlay dismissal).

    Args:
        page: The Playwright Page object.
        initial_result: The result of the initial failed action.
        action_func: Function that executes the action (takes no args).
        registry: The ElementRegistry for overlay detection.
        max_attempts: Maximum number of retry attempts (default 3).
        initial_backoff: Initial backoff time in seconds (default 1.0).

    Returns:
        RetryResult with success status, final ActionResult, and attempts made.
    """
    if initial_result.success:
        return RetryResult(
            success=True,
            final_result=initial_result,
            attempts_made=[],
        )

    attempts: list[RetryAttempt] = []
    last_result = initial_result

    for attempt_num in range(max_attempts):
        # Calculate backoff time with exponential increase: 1s, 2s, 4s, ...
        backoff = initial_backoff * (2**attempt_num)

        # Choose a different strategy for each attempt
        if attempt_num == 0:
            # First retry: Re-observe and handle overlays
            strategy = "reobserve_and_dismiss"
            description = f"Re-observing page and checking for overlays (backoff: {backoff}s)"

            # Wait before retrying
            time.sleep(backoff)

            # The re-observation should be done by the caller
            # This retry attempt signals that re-observation is needed
            attempt = RetryAttempt(strategy, description)
            attempts.append(attempt)

            # Signal caller to re-observe and retry
            return RetryResult(
                success=False,
                final_result=last_result,
                attempts_made=attempts,
                should_ask_user=False,
            )

        elif attempt_num == 1:
            # Second retry: Wait for network/selector stability
            strategy = "wait_for_stability"
            description = f"Waiting for network/selector stability (backoff: {backoff}s)"

            time.sleep(backoff)

            # Try waiting for load state
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
                logForDebugging("Network idle achieved")
            except PlaywrightTimeoutError:
                logForDebugging("Network idle timeout - continuing anyway", level="warning")
            except Exception as e:
                logError(
                    ErrorIds.OVERLAY_DISMISS_FAILED,
                    "Error waiting for network idle",
                    exc_info=False
                )

            attempt = RetryAttempt(strategy, description)
            attempts.append(attempt)

            # Try the action again
            try:
                last_result = action_func()
                if last_result.success:
                    logEvent("retry_succeeded", {"attempt": attempt_num + 1})
                    return RetryResult(
                        success=True,
                        final_result=last_result,
                        attempts_made=attempts,
                    )
            except Exception as e:
                logError(
                    ErrorIds.UNEXPECTED_ERROR,
                    f"Retry attempt {attempt_num + 1} failed",
                    exc_info=False
                )
                last_result = failure_result(
                    message=f"Retry attempt {attempt_num + 1} failed",
                    error=str(e),
                )

        elif attempt_num == 2:
            # Third retry: Wait longer and check for new overlays
            strategy = "extended_wait_and_overlay_check"
            description = f"Extended wait with overlay check (backoff: {backoff}s)"

            time.sleep(backoff)

            # Check for any new overlays that might have appeared
            from browser_agent.tools.observe import browser_observe

            try:
                snapshot = browser_observe(page, registry)
                overlays_found, overlay_msg = detect_and_handle_overlays(
                    page, snapshot, registry
                )
                if overlays_found:
                    description += f" - {overlay_msg}"

                    # Try the action again after dismissing overlays
                    last_result = action_func()
                    if last_result.success:
                        logEvent("retry_succeeded", {"attempt": attempt_num + 1})
                        attempt = RetryAttempt(strategy, description)
                        attempts.append(attempt)
                        return RetryResult(
                            success=True,
                            final_result=last_result,
                            attempts_made=attempts,
                        )
            except Exception as e:
                logError(
                    ErrorIds.OVERLAY_DETECTION_FAILED,
                    "Error during overlay check",
                    exc_info=False
                )

            attempt = RetryAttempt(strategy, description)
            attempts.append(attempt)

    # All retries exhausted - log and ask user for guidance
    logError(
        ErrorIds.RETRY_EXHAUSTED,
        f"All {max_attempts} retry attempts exhausted"
    )
    return RetryResult(
        success=False,
        final_result=last_result,
        attempts_made=attempts,
        should_ask_user=True,
    )


class StuckDetector:
    """Detects when the agent is stuck in a loop without making progress.

    Tracks consecutive actions without progress and determines when
    user intervention is needed.
    """

    def __init__(self, stuck_threshold: int = 5) -> None:
        """Initialize the stuck detector.

        Args:
            stuck_threshold: Number of actions without progress before considering stuck.
                           Default is 5.
        """
        self._stuck_threshold = stuck_threshold
        self._consecutive_failures: int = 0
        self._url_history: list[str] = []
        self._last_snapshot_version: int = 0
        self._actions_since_progress: int = 0

    def record_action(
        self,
        result: ActionResult,
        current_url: str = "",
        snapshot_version: int = 0,
    ) -> None:
        """Record an action result for stuck detection.

        Args:
            result: The ActionResult from the action.
            current_url: The current page URL (for navigation tracking).
            snapshot_version: The current page snapshot version.
        """
        if result.success:
            # Check if we made actual progress
            if self._is_progress(result, current_url, snapshot_version):
                self._actions_since_progress = 0
                self._consecutive_failures = 0
            else:
                self._actions_since_progress += 1
        else:
            self._consecutive_failures += 1
            self._actions_since_progress += 1

        # Update URL history
        if current_url and current_url not in self._url_history:
            self._url_history.append(current_url)

        self._last_snapshot_version = snapshot_version

    def _is_progress(
        self,
        result: ActionResult,
        current_url: str,
        snapshot_version: int,
    ) -> bool:
        """Check if this result represents meaningful progress.

        Args:
            result: The ActionResult from the action.
            current_url: The current page URL.
            snapshot_version: The current page snapshot version.

        Returns:
            True if meaningful progress was made.
        """
        # New snapshot version indicates page changed
        if result.new_snapshot and result.new_snapshot.version > self._last_snapshot_version:
            return True

        # Navigation to a new URL is progress
        if current_url and current_url not in self._url_history[-3:]:
            return True

        # DONE action is always progress
        if "task completed" in (result.message or "").lower():
            return True

        return False

    def is_stuck(self) -> bool:
        """Check if the agent appears to be stuck.

        Returns:
            True if stuck threshold has been exceeded.
        """
        return (
            self._consecutive_failures >= self._stuck_threshold
            or self._actions_since_progress >= self._stuck_threshold * 2
        )

    def get_stuck_message(self) -> str:
        """Get a message describing why the agent appears stuck.

        Returns:
            A human-readable message about the stuck state.
        """
        parts = []

        if self._consecutive_failures >= self._stuck_threshold:
            parts.append(
                f"{self._consecutive_failures} consecutive failures"
            )

        if self._actions_since_progress >= self._stuck_threshold * 2:
            parts.append(
                f"{self._actions_since_progress} actions without meaningful progress"
            )

        if self._url_history:
            if len(self._url_history) <= 3:
                parts.append(
                    f"only visited {len(self._url_history)} URL(s): {', '.join(self._url_history)}"
                )
            else:
                parts.append(
                    f"navigating between same {len(self._url_history)} URLs"
                )

        return "Agent appears stuck: " + ", ".join(parts) + "."

    def reset(self) -> None:
        """Reset the stuck detector state."""
        self._consecutive_failures = 0
        self._actions_since_progress = 0


def detect_stuck(
    consecutive_failures: int,
    actions_without_progress: int,
    stuck_threshold: int = 5,
) -> tuple[bool, str]:
    """Simple stuck detection function.

    Args:
        consecutive_failures: Number of consecutive failed actions.
        actions_without_progress: Number of actions without meaningful progress.
        stuck_threshold: Threshold for considering the agent stuck (default 5).

    Returns:
        A tuple of (is_stuck, message):
        - is_stuck: True if stuck threshold exceeded
        - message: Human-readable description of the stuck state
    """
    if consecutive_failures >= stuck_threshold:
        return (
            True,
            f"Agent has {consecutive_failures} consecutive failures. "
            f"This may indicate a login issue, 2FA requirement, or blocked action."
        )

    if actions_without_progress >= stuck_threshold * 2:
        return (
            True,
            f"Agent has performed {actions_without_progress} actions without progress. "
            f"An alternative approach or user guidance may be needed."
        )

    return False, ""

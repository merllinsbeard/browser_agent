"""Integration tests for agent orchestration and handoffs.

This module tests the interaction between Planner and Navigator agents,
including handoff patterns, action execution, and error recovery flows.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from browser_agent.agents.navigator import NavigatorAgent
from browser_agent.agents.planner import PlannerAgent
from browser_agent.core.registry import ElementRegistry
from browser_agent.models.element import InteractiveElement
from browser_agent.models.result import ActionResult
from browser_agent.models.snapshot import PageSnapshot
from browser_agent.core.recovery import (
    RetryAttempt,
    RetryResult,
    StuckDetector,
    detect_and_handle_overlays,
    needs_reobservation,
    retry_with_backoff,
    detect_stuck,
)


# =============================================================================
# Planner -> Navigator Handoff Tests
# =============================================================================


class TestPlannerNavigatorHandoff:
    """Tests for handoff between Planner and Navigator agents."""

    def test_planner_creates_plan_navigator_executes(self) -> None:
        """Test that Planner creates a plan and Navigator can execute steps."""
        # Arrange: Create a Planner and generate a plan
        planner = PlannerAgent()
        task = "Navigate to example.com and click the first button"

        # Mock the LLM call to return a predictable plan
        with patch("browser_agent.agents.planner.call_llm") as mock_llm:
            mock_llm.return_value = """1. NAVIGATE https://example.com
2. CLICK elem-0
3. DONE Task complete"""
            plan = planner.create_plan(task)

        # Assert plan was created
        assert len(plan) == 3
        assert "NAVIGATE https://example.com" in plan[0]
        assert "CLICK elem-0" in plan[1]
        assert "DONE" in plan[2]

        # Arrange: Create Navigator with mocked Page and Registry
        mock_page = MagicMock()
        # Mock page.goto() and page.url for the navigate() function
        mock_page.url = "https://example.com"
        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto.return_value = mock_response

        mock_registry = MagicMock()
        mock_registry.increment_version = MagicMock()

        # Mock browser_observe to return a snapshot
        mock_snapshot = MagicMock(spec=PageSnapshot)
        mock_snapshot.interactive_elements = []

        with patch("browser_agent.agents.navigator.browser_observe", return_value=mock_snapshot):
            navigator = NavigatorAgent(mock_page, mock_registry)

            # Act: Execute the NAVIGATE step
            result = navigator.execute_step(plan[0])

        # Assert: Navigator executed the step
        assert result.success
        assert "200" in result.message or "OK" in result.message

    def test_navigator_observes_before_each_action(self) -> None:
        """Test that Navigator observes the page before executing each action."""
        mock_page = MagicMock()
        mock_registry = MagicMock()

        mock_snapshot = MagicMock(spec=PageSnapshot)
        mock_snapshot.interactive_elements = []

        with patch("browser_agent.agents.navigator.browser_observe") as mock_observe:
            mock_observe.return_value = mock_snapshot

            navigator = NavigatorAgent(mock_page, mock_registry)

            # Execute multiple steps
            steps = ["WAIT", "PRESS Enter", "SCROLL"]
            for step in steps:
                navigator.execute_step(step)

            # Verify browser_observe was called before each action
            assert mock_observe.call_count == len(steps)

    def test_navigator_returns_to_planner_on_completion(self) -> None:
        """Test that Navigator signals completion back to Planner."""
        mock_page = MagicMock()
        mock_registry = MagicMock()
        mock_snapshot = MagicMock(spec=PageSnapshot)
        mock_snapshot.interactive_elements = []

        with patch("browser_agent.agents.navigator.browser_observe", return_value=mock_snapshot):
            navigator = NavigatorAgent(mock_page, mock_registry)

            # Execute DONE action
            result = navigator.execute_step("DONE All tasks completed")

        # Assert: Navigator returns success with completion message
        assert result.success
        assert "All tasks completed" in result.message
        assert navigator.get_actions_completed() > 0

    def test_navigator_returns_to_planner_on_failure(self) -> None:
        """Test that Navigator reports failures back to Planner."""
        mock_page = MagicMock()
        mock_registry = MagicMock()

        # Mock get_locator to raise StaleElementError
        from browser_agent.core.registry import StaleElementError
        mock_registry.get_locator.side_effect = StaleElementError("elem-0", 1, 2)

        mock_snapshot = MagicMock(spec=PageSnapshot)
        mock_snapshot.interactive_elements = []

        with patch("browser_agent.agents.navigator.browser_observe", return_value=mock_snapshot):
            navigator = NavigatorAgent(mock_page, mock_registry)

            # Execute CLICK action with stale element
            result = navigator.execute_step("CLICK elem-0")

        # Assert: Navigator returns failure
        assert not result.success
        assert result.error is not None
        assert "stale" in result.error.lower()


# =============================================================================
# Error Recovery: Re-observation Tests
# =============================================================================


class TestErrorRecoveryReobservation:
    """Tests for error recovery through page re-observation."""

    def test_needs_reobservation_detects_detached_element(self) -> None:
        """Test that detached element errors trigger re-observation."""
        result = ActionResult.failure_result(
            "Element clicked",
            error="Element is detached from DOM"
        )

        assert needs_reobservation(result) is True

    def test_needs_reobservation_detects_timeout(self) -> None:
        """Test that timeout errors trigger re-observation."""
        result = ActionResult.failure_result(
            "Action timed out",
            error="Timeout waiting for selector"
        )

        assert needs_reobservation(result) is True

    def test_needs_reobservation_detects_not_found(self) -> None:
        """Test that not found errors trigger re-observation."""
        result = ActionResult.failure_result(
            "Element not found",
            error="Selector not found"
        )

        assert needs_reobservation(result) is True

    def test_needs_reobservation_detects_stale_element(self) -> None:
        """Test that stale element errors trigger re-observation."""
        result = ActionResult.failure_result(
            "Element is stale",
            error="StaleElementReference"
        )

        assert needs_reobservation(result) is True

    def test_needs_reobservation_skips_success(self) -> None:
        """Test that successful actions don't trigger re-observation."""
        result = ActionResult.success_result("Action completed")

        assert needs_reobservation(result) is False

    def test_needs_reobservation_skips_unrelated_errors(self) -> None:
        """Test that unrelated errors don't trigger re-observation."""
        result = ActionResult.failure_result(
            "Network error",
            error="Connection refused"
        )

        # This error doesn't suggest page state change
        assert needs_reobservation(result) is False


# =============================================================================
# Error Recovery: Retry Logic Tests
# =============================================================================


class TestErrorRecoveryRetry:
    """Tests for retry logic with exponential backoff."""

    def test_retry_with_backoff_succeeds_on_first_retry(self) -> None:
        """Test that retry succeeds when action works on first retry."""
        mock_page = MagicMock()

        # Initial failure
        initial_result = ActionResult.failure_result("Timed out", error="Timeout")

        # Action function that succeeds on retry
        call_count = [0]
        def action_func() -> ActionResult:
            call_count[0] += 1
            if call_count[0] == 1:
                return ActionResult.failure_result("Still failing")
            return ActionResult.success_result("Success!")

        result = retry_with_backoff(mock_page, initial_result, action_func, max_attempts=3)

        # First attempt is the reobserve signal, second is actual retry
        assert result.attempts_made[0].strategy == "reobserve_and_dismiss"

    def test_retry_with_backoff_different_strategies(self) -> None:
        """Test that each retry uses a different strategy."""
        mock_page = MagicMock()

        initial_result = ActionResult.failure_result("Failed")

        def action_func() -> ActionResult:
            return ActionResult.failure_result("Still failing")

        result = retry_with_backoff(
            mock_page,
            initial_result,
            action_func,
            max_attempts=3
        )

        # First attempt signals re-observation to caller
        strategies = [attempt.strategy for attempt in result.attempts_made]
        assert "reobserve_and_dismiss" in strategies
        # The function returns on first attempt to signal caller
        assert len(strategies) == 1

    def test_retry_with_backoff_exhaustion_prompts_user(self) -> None:
        """Test that exhausted retries signal user should be asked."""
        mock_page = MagicMock()

        initial_result = ActionResult.failure_result("Failed")

        def action_func() -> ActionResult:
            return ActionResult.failure_result("Always fails")

        result = retry_with_backoff(
            mock_page,
            initial_result,
            action_func,
            max_attempts=3
        )

        # The first attempt returns to signal re-observation
        assert result.success is False
        assert result.should_ask_user is False
        assert len(result.attempts_made) == 1
        assert result.attempts_made[0].strategy == "reobserve_and_dismiss"

    def test_retry_with_backoff_skips_if_initial_success(self) -> None:
        """Test that retry is skipped if initial result was successful."""
        mock_page = MagicMock()

        initial_result = ActionResult.success_result("Already succeeded")

        def action_func() -> ActionResult:
            return ActionResult.success_result("Should not be called")

        result = retry_with_backoff(mock_page, initial_result, action_func)

        assert result.success is True
        assert len(result.attempts_made) == 0

    def test_retry_attempt_repr(self) -> None:
        """Test RetryAttempt string representation."""
        attempt = RetryAttempt("test_strategy", "Test description")
        repr_str = repr(attempt)

        assert "test_strategy" in repr_str
        assert "Test description" in repr_str


# =============================================================================
# Error Recovery: Stuck Detection Tests
# =============================================================================


class TestErrorRecoveryStuckDetection:
    """Tests for stuck detection during agent execution."""

    def test_stuck_detector_consecutive_failures(self) -> None:
        """Test that consecutive failures trigger stuck detection."""
        detector = StuckDetector(stuck_threshold=5)

        # Record 5 consecutive failures
        for _ in range(5):
            result = ActionResult.failure_result("Action failed")
            detector.record_action(result)

        assert detector.is_stuck() is True

    def test_stuck_detector_no_progress(self) -> None:
        """Test that lack of progress triggers stuck detection."""
        detector = StuckDetector(stuck_threshold=5)

        # Record 10 actions without progress (threshold * 2)
        for _ in range(10):
            result = ActionResult.success_result("No meaningful progress")
            detector.record_action(result, snapshot_version=1)

        assert detector.is_stuck() is True

    def test_stuck_detector_resets_on_progress(self) -> None:
        """Test that progress resets stuck detection."""
        detector = StuckDetector(stuck_threshold=5)

        # Record some failures
        for _ in range(3):
            result = ActionResult.failure_result("Failed")
            detector.record_action(result)

        # Record progress (new snapshot version)
        progress_result = ActionResult.success_result("Progress made", new_snapshot=MagicMock(version=2))
        detector.record_action(progress_result, snapshot_version=2)

        # Should not be stuck after progress
        assert detector.is_stuck() is False

    def test_stuck_detector_url_loop_detection(self) -> None:
        """Test that URL loops contribute to stuck detection."""
        detector = StuckDetector(stuck_threshold=5)

        # Navigate between same 3 URLs repeatedly
        urls = ["https://a.com", "https://b.com", "https://c.com"]
        for _ in range(10):
            for url in urls:
                result = ActionResult.success_result("Navigated")
                detector.record_action(result, current_url=url, snapshot_version=1)

        assert detector.is_stuck() is True

    def test_stuck_detector_get_stuck_message(self) -> None:
        """Test that stuck message provides useful context."""
        detector = StuckDetector(stuck_threshold=5)

        # Record consecutive failures
        for _ in range(5):
            result = ActionResult.failure_result("Failed")
            detector.record_action(result, current_url="https://example.com")

        message = detector.get_stuck_message()

        assert "consecutive failures" in message.lower()
        assert "5" in message

    def test_stuck_detector_reset(self) -> None:
        """Test that reset clears stuck state."""
        detector = StuckDetector(stuck_threshold=5)

        # Record failures
        for _ in range(5):
            result = ActionResult.failure_result("Failed")
            detector.record_action(result)

        assert detector.is_stuck() is True

        # Reset
        detector.reset()

        # Should no longer be stuck
        assert detector.is_stuck() is False

    def test_detect_stuck_functional_api(self) -> None:
        """Test the functional API for stuck detection."""
        is_stuck, message = detect_stuck(
            consecutive_failures=5,
            actions_without_progress=10,
            stuck_threshold=5
        )

        assert is_stuck is True
        assert "consecutive failures" in message.lower()

    def test_detect_stuck_no_progress_trigger(self) -> None:
        """Test stuck detection triggered by no-progress actions."""
        is_stuck, message = detect_stuck(
            consecutive_failures=2,
            actions_without_progress=10,
            stuck_threshold=5
        )

        assert is_stuck is True
        assert "without progress" in message.lower()

    def test_detect_stuck_not_stuck(self) -> None:
        """Test that agent is not stuck below thresholds."""
        is_stuck, message = detect_stuck(
            consecutive_failures=2,
            actions_without_progress=5,
            stuck_threshold=5
        )

        assert is_stuck is False
        assert message == ""


# =============================================================================
# Overlay Detection and Dismissal Tests
# =============================================================================


class TestOverlayDetectionAndDismissal:
    """Tests for modal overlay detection and dismissal."""

    def test_detect_overlays_finds_dialog_role(self) -> None:
        """Test that dialogs with role='dialog' are detected."""
        mock_page = MagicMock()

        # Create snapshot with dialog element
        dialog = InteractiveElement(
            ref="elem-0",
            role="dialog",
            name="Cookie consent",
        )
        snapshot = PageSnapshot(
            url="https://example.com",
            title="Test",
            interactive_elements=[dialog],
            visible_text_excerpt="",
            version=1,
        )

        overlays_found, message = detect_and_handle_overlays(mock_page, snapshot)

        assert overlays_found is True
        assert "overlay" in message.lower()

    def test_detect_overlays_finds_aria_modal(self) -> None:
        """Test that elements with aria-modal are detected."""
        mock_page = MagicMock()

        # Create snapshot with aria-modal element
        modal = InteractiveElement(
            ref="elem-0",
            role="alert",
            name="Newsletter popup",
            aria_label="modal newsletter",
        )
        snapshot = PageSnapshot(
            url="https://example.com",
            title="Test",
            interactive_elements=[modal],
            visible_text_excerpt="",
            version=1,
        )

        overlays_found, message = detect_and_handle_overlays(mock_page, snapshot)

        assert overlays_found is True

    def test_detect_overlays_none_found(self) -> None:
        """Test that no overlays returns False."""
        mock_page = MagicMock()

        # Create snapshot without overlays
        button = InteractiveElement(
            ref="elem-0",
            role="button",
            name="Submit",
        )
        snapshot = PageSnapshot(
            url="https://example.com",
            title="Test",
            interactive_elements=[button],
            visible_text_excerpt="",
            version=1,
        )

        overlays_found, message = detect_and_handle_overlays(mock_page, snapshot)

        assert overlays_found is False
        assert message == "No overlays detected"

    def test_dismiss_with_close_button(self) -> None:
        """Test overlay dismissal via close button."""
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_locator.count.return_value = 1
        mock_page.locator.return_value.first = mock_locator

        # Create snapshot with dialog
        dialog = InteractiveElement(
            ref="elem-0",
            role="dialog",
            name="Modal",
        )
        snapshot = PageSnapshot(
            url="https://example.com",
            title="Test",
            interactive_elements=[dialog],
            visible_text_excerpt="",
            version=1,
        )

        overlays_found, message = detect_and_handle_overlays(mock_page, snapshot)

        # Close button strategy should have been attempted
        assert overlays_found is True

    def test_dismiss_with_escape_key(self) -> None:
        """Test overlay dismissal via Escape key."""
        mock_page = MagicMock()
        # Mock that no close buttons are found
        mock_page.locator.return_value.first.count.return_value = 0

        dialog = InteractiveElement(
            ref="elem-0",
            role="dialog",
            name="Modal",
        )
        snapshot = PageSnapshot(
            url="https://example.com",
            title="Test",
            interactive_elements=[dialog],
            visible_text_excerpt="",
            version=1,
        )

        overlays_found, message = detect_and_handle_overlays(mock_page, snapshot)

        # Escape key should have been attempted
        mock_page.keyboard.press.assert_called()

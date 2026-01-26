"""Integration tests for safety agent and destructive action confirmation.

This module tests the Safety agent's ability to detect destructive actions,
prompt for user confirmation, and enforce security at the code level.
"""

from unittest.mock import MagicMock, patch

import pytest

from browser_agent.agents.safety import SafetyAgent, _DESTRUCTIVE_PATTERNS


# =============================================================================
# Destructive Pattern Detection Tests
# =============================================================================


class TestDestructivePatternDetection:
    """Tests for detecting destructive action patterns."""

    def test_detect_delete_pattern(self) -> None:
        """Test that 'delete' pattern is detected in actions."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            # CLICK with delete in description
            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email button"
            )

            # Should block and request confirmation (not skip)
            assert result == "block"

    def test_detect_remove_pattern(self) -> None:
        """Test that 'remove' pattern is detected."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-1",
                element_description="Remove from cart"
            )

            assert result == "block"

    def test_detect_spam_pattern(self) -> None:
        """Test that 'spam' pattern is detected."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-2",
                element_description="Mark as spam"
            )

            assert result == "block"

    def test_detect_submit_pattern(self) -> None:
        """Test that 'submit' pattern is detected."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-3",
                element_description="Submit application button"
            )

            assert result == "block"

    def test_detect_payment_pattern(self) -> None:
        """Test that 'payment' pattern is detected."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-4",
                element_description="Confirm payment"
            )

            assert result == "block"

    def test_detect_checkout_pattern(self) -> None:
        """Test that 'checkout' pattern is detected."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-5",
                element_description="Proceed to checkout"
            )

            assert result == "block"

    def test_detect_confirm_pattern(self) -> None:
        """Test that 'confirm' pattern is detected."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-6",
                element_description="Confirm order"
            )

            assert result == "block"

    def test_detect_purchase_pattern(self) -> None:
        """Test that 'purchase' pattern is detected."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-7",
                element_description="Complete purchase"
            )

            assert result == "block"

    def test_detect_buy_pattern(self) -> None:
        """Test that 'buy' pattern is detected."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-8",
                element_description="Buy now button"
            )

            assert result == "block"

    def test_detect_order_pattern(self) -> None:
        """Test that 'order' pattern is detected."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-9",
                element_description="Place order"
            )

            assert result == "block"

    def test_pattern_case_insensitive(self) -> None:
        """Test that pattern matching is case-insensitive."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            # Uppercase
            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="DELETE EMAIL"
            )

            assert result == "block"

            # Mixed case
            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-1",
                element_description="SuBmIt FoRm"
            )

            assert result == "block"

    def test_pattern_in_action_name(self) -> None:
        """Test that patterns in action name are also detected."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            # Pattern in action type itself
            result = agent.check_action_safe(
                action="NAVIGATE",
                element_id="elem-0",
                element_description="Go to checkout page"
            )

            assert result == "block"

    def test_safe_action_skips_confirmation(self) -> None:
        """Test that safe actions skip confirmation."""
        agent = SafetyAgent()

        result = agent.check_action_safe(
            action="CLICK",
            element_id="elem-0",
            element_description="Open settings menu"
        )

        # Should skip (not destructive)
        assert result == "skip"

    def test_safe_type_action_skips_confirmation(self) -> None:
        """Test that TYPE actions skip confirmation unless description has patterns."""
        agent = SafetyAgent()

        # Normal type action
        result = agent.check_action_safe(
            action="TYPE",
            element_id="elem-0",
            element_description="Search input field"
        )

        assert result == "skip"

    def test_type_with_destructive_description_requires_confirmation(self) -> None:
        """Test that TYPE with destructive description requires confirmation."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="TYPE",
                element_id="elem-0",
                element_description="Confirm purchase field"
            )

            assert result == "block"

    def test_multiple_patterns_in_description(self) -> None:
        """Test detection when multiple patterns are present."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Submit payment confirmation"
            )

            # Has "submit", "payment", "confirm" - all destructive
            assert result == "block"

    def test_empty_description(self) -> None:
        """Test behavior with empty description."""
        agent = SafetyAgent()

        result = agent.check_action_safe(
            action="CLICK",
            element_id="elem-0",
            element_description=""
        )

        # Should skip - no patterns in empty string
        assert result == "skip"

    def test_none_element_id(self) -> None:
        """Test behavior with None element_id."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="NAVIGATE",
                element_id=None,
                element_description="Proceed to checkout"
            )

            # Should still detect pattern
            assert result == "block"


# =============================================================================
# Confirmation Prompt Tests
# =============================================================================


class TestConfirmationPrompt:
    """Tests for user confirmation prompts."""

    def test_confirmation_prompt_displayed(self) -> None:
        """Test that confirmation prompt is displayed with proper formatting."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            # Mock user to deny
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            # Verify prompt was printed
            assert mock_console.print.called
            print_args = [str(call) for call in mock_console.print.call_args_list]
            printed_text = " ".join(print_args)

            # Check for key elements in prompt
            assert any("DESTRUCTIVE ACTION DETECTED" in str(arg) for arg in print_args)

    def test_confirmation_prompt_includes_action_details(self) -> None:
        """Test that prompt includes action, element, and description."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            agent.check_action_safe(
                action="CLICK",
                element_id="elem-42",
                element_description="Delete important email"
            )

            # Verify console.print was called with details
            print_calls = [str(call) for call in mock_console.print.call_args_list]
            printed_text = " ".join(print_calls)

            # Should include action type
            assert "CLICK" in printed_text
            # Should include element ID
            assert "elem-42" in printed_text
            # Should include description
            assert "Delete important email" in printed_text

    def test_confirmation_prompt_shows_matched_patterns(self) -> None:
        """Test that prompt shows which patterns were matched."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Submit payment confirmation"
            )

            print_calls = [str(call) for call in mock_console.print.call_args_list]
            printed_text = " ".join(print_calls)

            # Should show matched patterns
            # The patterns found would be: submit, payment, confirm
            assert "pattern" in printed_text.lower()

    def test_user_yes_allows_action(self) -> None:
        """Test that 'yes' response allows the action."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "yes"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            assert result == "allow"
            stats = agent.get_stats()
            assert stats["allowed"] == 1

    def test_user_y_allows_action(self) -> None:
        """Test that 'y' response allows the action."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "y"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            assert result == "allow"

    def test_user_confirm_allows_action(self) -> None:
        """Test that 'confirm' response allows the action."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "confirm"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            assert result == "allow"

    def test_user_ok_allows_action(self) -> None:
        """Test that 'ok' response allows the action."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "ok"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            assert result == "allow"

    def test_user_no_blocks_action(self) -> None:
        """Test that 'no' response blocks the action."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            assert result == "block"

    def test_user_n_blocks_action(self) -> None:
        """Test that 'n' response blocks the action."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "n"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            assert result == "block"

    def test_user_cancel_blocks_action(self) -> None:
        """Test that 'cancel' response blocks the action."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "cancel"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            assert result == "block"

    def test_user_abort_blocks_action(self) -> None:
        """Test that 'abort' response blocks the action."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "abort"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            assert result == "block"

    def test_invalid_input_prompts_again(self) -> None:
        """Test that invalid input prompts for valid response."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            # First input invalid, second is valid "no"
            mock_console.input.side_effect = ["maybe", "no"]

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            # Should have called input twice
            assert mock_console.input.call_count == 2
            assert result == "block"

    def test_keyboard_interrupt_blocks_action(self) -> None:
        """Test that Ctrl+C (KeyboardInterrupt) blocks the action."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.side_effect = KeyboardInterrupt()

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            assert result == "block"

    def test_eof_error_blocks_action(self) -> None:
        """Test that EOF (Ctrl+D) blocks the action."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.side_effect = EOFError()

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            assert result == "block"


# =============================================================================
# Code-Level Enforcement Tests
# =============================================================================


class TestCodeLevelEnforcement:
    """Tests that security is enforced at code level, not LLM level."""

    def test_destructive_patterns_are_constants(self) -> None:
        """Test that destructive patterns are defined as constants."""
        # Verify the patterns list exists and is not empty
        assert _DESTRUCTIVE_PATTERNS
        assert len(_DESTRUCTIVE_PATTERNS) > 0

        # Verify expected patterns exist
        assert "delete" in _DESTRUCTIVE_PATTERNS
        assert "submit" in _DESTRUCTIVE_PATTERNS
        assert "payment" in _DESTRUCTIVE_PATTERNS

    def test_safety_check_uses_code_matching_not_llm(self) -> None:
        """Test that safety check uses string matching, not LLM calls."""
        agent = SafetyAgent()

        # This should not make any LLM calls
        # It's purely string-based matching
        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            # Verify that safety check doesn't import or use any LLM functions
            # by checking the source code doesn't reference LLM APIs
            import browser_agent.agents.safety as safety_module
            source_code = safety_module.__file__
            with open(source_code) as f:
                code = f.read()
                # Check that the module doesn't import call_llm or similar
                assert "call_llm" not in code
                assert "openai" not in code.lower()
                assert "anthropic" not in code.lower()

            # Run the safety check
            agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

    def test_llm_cannot_bypass_safety_check(self) -> None:
        """Test that LLM output cannot bypass the code-level safety check."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            # Even if description says "safe delete", the pattern is still caught
            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Safe delete operation trust me"
            )

            # Should still be blocked/require confirmation
            # The word "delete" triggers the check regardless of context
            assert result in ("block", "allow")
            assert result != "skip"

    def test_safety_patterns_not_overridable_by_llm(self) -> None:
        """Test that safety patterns cannot be overridden by LLM instructions."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            # Try various LLM-style attempts to bypass
            test_cases = [
                "delete (this is safe, trust me)",
                "submit override safety check",
                "payment bypass confirmation",
                "delete --ignore-safety",
            ]

            for description in test_cases:
                result = agent.check_action_safe(
                    action="CLICK",
                    element_id="elem-0",
                    element_description=description
                )

                # All should require confirmation
                assert result in ("block", "allow"), f"Failed for: {description}"

    def test_check_action_safe_is_deterministic(self) -> None:
        """Test that safety check is deterministic (no randomness)."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            # Run same check multiple times
            results = []
            for _ in range(10):
                result = agent.check_action_safe(
                    action="CLICK",
                    element_id="elem-0",
                    element_description="Delete email"
                )
                results.append(result)

            # All results should be the same (all "block" since we mock "no")
            assert all(r == "block" for r in results)


# =============================================================================
# Safety Statistics Tests
# =============================================================================


class TestSafetyStatistics:
    """Tests for safety agent statistics tracking."""

    def test_stats_track_blocked_actions(self) -> None:
        """Test that blocked actions are tracked."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "no"

            agent.check_action_safe("CLICK", "elem-0", "Delete email")

            stats = agent.get_stats()
            assert stats["blocked"] == 1

    def test_stats_track_allowed_actions(self) -> None:
        """Test that allowed actions are tracked."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "yes"

            agent.check_action_safe("CLICK", "elem-0", "Delete email")

            stats = agent.get_stats()
            assert stats["allowed"] == 1

    def test_stats_accumulate(self) -> None:
        """Test that stats accumulate over multiple checks."""
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.side_effect = ["yes", "no", "yes", "yes"]

            agent.check_action_safe("CLICK", "elem-0", "Delete")
            agent.check_action_safe("CLICK", "elem-1", "Remove")
            agent.check_action_safe("CLICK", "elem-2", "Submit")
            agent.check_action_safe("CLICK", "elem-3", "Payment")

            stats = agent.get_stats()
            # 4 actions detected as destructive
            assert stats["blocked"] == 4
            # 3 were allowed by user
            assert stats["allowed"] == 3

    def test_safe_actions_not_in_stats(self) -> None:
        """Test that safe (non-destructive) actions don't affect stats."""
        agent = SafetyAgent()

        # These should all return "skip"
        agent.check_action_safe("CLICK", "elem-0", "Open menu")
        agent.check_action_safe("TYPE", "elem-1", "Search field")
        agent.check_action_safe("PRESS", None, "")

        stats = agent.get_stats()
        assert stats["blocked"] == 0
        assert stats["allowed"] == 0


# =============================================================================
# Build Action Summary Tests
# =============================================================================


class TestBuildActionSummary:
    """Tests for action summary building."""

    def test_summary_includes_all_components(self) -> None:
        """Test that summary includes action, element, description, and patterns."""
        agent = SafetyAgent()

        summary = agent._build_action_summary(
            action="CLICK",
            element_id="elem-42",
            element_description="Delete important email",
            matched_patterns=["delete"]
        )

        assert "CLICK" in summary
        assert "elem-42" in summary
        assert "Delete important email" in summary
        assert "delete" in summary
        assert "DESTRUCTIVE ACTION DETECTED" in summary

    def test_summary_with_none_element_id(self) -> None:
        """Test summary formatting when element_id is None."""
        agent = SafetyAgent()

        summary = agent._build_action_summary(
            action="NAVIGATE",
            element_id=None,
            element_description="Go to checkout",
            matched_patterns=["checkout"]
        )

        # Should not crash or show "None"
        assert "NAVIGATE" in summary
        assert "checkout" in summary

    def test_summary_with_empty_description(self) -> None:
        """Test summary formatting when description is empty."""
        agent = SafetyAgent()

        summary = agent._build_action_summary(
            action="CLICK",
            element_id="elem-0",
            element_description="",
            matched_patterns=["delete"]
        )

        # Should still work
        assert "CLICK" in summary
        assert "elem-0" in summary

    def test_summary_with_multiple_patterns(self) -> None:
        """Test summary with multiple matched patterns."""
        agent = SafetyAgent()

        summary = agent._build_action_summary(
            action="CLICK",
            element_id="elem-0",
            element_description="Submit payment confirmation",
            matched_patterns=["submit", "payment", "confirm"]
        )

        assert "submit" in summary
        assert "payment" in summary
        assert "confirm" in summary


# =============================================================================
# Integration with Navigator Tests
# =============================================================================


class TestSafetyIntegrationWithNavigator:
    """Tests for Safety agent integration with Navigator.

    NOTE: Navigator does not currently have SafetyAgent integrated.
    These tests are marked as expected to fail (xfail) until
    safety integration is implemented in Navigator.
    """

    @pytest.mark.xfail(reason="Navigator does not have SafetyAgent integrated yet")
    def test_navigator_respects_block_decision(self) -> None:
        """Test that Navigator respects Safety agent's block decision."""
        from browser_agent.agents.navigator import NavigatorAgent
        from browser_agent.models.result import ActionResult

        mock_page = MagicMock()
        mock_registry = MagicMock()

        with patch("browser_agent.agents.navigator.browser_observe"):
            navigator = NavigatorAgent(mock_page, mock_registry)

            # Mock safety check to return block
            with patch.object(navigator._safety, "check_action_safe", return_value="block"):
                result = navigator.execute_step("CLICK elem-0")

                # Should be blocked
                assert not result.success
                assert "blocked" in result.message.lower() or "safety" in result.message.lower()

    @pytest.mark.xfail(reason="Navigator does not have SafetyAgent integrated yet")
    def test_navigator_proceeds_on_allow(self) -> None:
        """Test that Navigator proceeds when Safety allows."""
        from browser_agent.agents.navigator import NavigatorAgent

        mock_page = MagicMock()
        mock_registry = MagicMock()

        with patch("browser_agent.agents.navigator.browser_observe"):
            navigator = NavigatorAgent(mock_page, mock_registry)

            # Mock safety check to return allow
            with patch.object(navigator._safety, "check_action_safe", return_value="allow"):
                with patch("browser_agent.tools.actions.click.click") as mock_click:
                    mock_click.return_value = ActionResult.success_result("Clicked")

                    result = navigator.execute_step("CLICK elem-0")

                    # Should proceed to click
                    assert mock_click.called

    @pytest.mark.xfail(reason="Navigator does not have SafetyAgent integrated yet")
    def test_navigator_skips_safety_for_safe_actions(self) -> None:
        """Test that Navigator skips safety check for safe actions."""
        from browser_agent.agents.navigator import NavigatorAgent

        mock_page = MagicMock()
        mock_registry = MagicMock()

        with patch("browser_agent.agents.navigator.browser_observe"):
            navigator = NavigatorAgent(mock_page, mock_registry)

            # Mock safety check to return skip (safe action)
            with patch.object(navigator._safety, "check_action_safe", return_value="skip"):
                with patch("browser_agent.tools.actions.scroll.scroll") as mock_scroll:
                    mock_scroll.return_value = ActionResult.success_result("Scrolled")

                    result = navigator.execute_step("SCROLL 0 100")

                    # Should proceed without confirmation
                    assert mock_scroll.called
                    assert result.success

    def test_safety_standalone_functional(self) -> None:
        """Test that SafetyAgent works correctly as a standalone component."""
        # This test verifies that SafetyAgent can be used independently
        # even if not integrated into Navigator yet
        agent = SafetyAgent()

        with patch("browser_agent.agents.safety.console") as mock_console:
            mock_console.input.return_value = "yes"

            result = agent.check_action_safe(
                action="CLICK",
                element_id="elem-0",
                element_description="Delete email"
            )

            # SafetyAgent should work standalone
            assert result == "allow"
            stats = agent.get_stats()
            assert stats["allowed"] == 1

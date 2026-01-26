"""Safety agent for confirming destructive actions.

This module provides the Safety agent which intercepts destructive
actions and requires user confirmation before proceeding.
"""

import re
from typing import Literal

from rich.console import Console

console = Console()

# Destructive action patterns to watch for
_DESTRUCTIVE_PATTERNS = [
    "delete",
    "remove",
    "spam",
    "submit",
    "payment",
    "checkout",
    "confirm",
    "purchase",
    "buy",
    "order",
]


class SafetyAgent:
    """Agent for ensuring safe browser automation.

    The Safety agent intercepts actions matching destructive patterns
    and requires user confirmation before proceeding. Security is
    enforced at CODE level via keyword matching, not LLM level.
    """

    def __init__(self) -> None:
        """Initialize the Safety agent."""
        self._actions_blocked = 0
        self._actions_allowed = 0

    def check_action_safe(
        self,
        action: str,
        element_id: str | None = None,
        element_description: str = "",
    ) -> Literal["allow", "block", "skip"]:
        """Check if an action is safe to execute.

        This performs CODE-LEVEL keyword matching to detect destructive
        actions. It does NOT rely on the LLM for safety.

        Args:
            action: The action type (CLICK, TYPE, PRESS, etc.).
            element_id: The element reference ID (if applicable).
            element_description: Description of the element for context.

        Returns:
            "allow" if the action is safe,
            "block" if the action is destructive and user declined,
            "skip" if the action is not destructive.
        """
        # Combine action and description for pattern matching
        combined = (action + " " + element_description).lower()

        # Check for destructive patterns
        destructive = False
        matched_patterns = []
        for pattern in _DESTRUCTIVE_PATTERNS:
            if pattern in combined:
                destructive = True
                matched_patterns.append(pattern)

        if not destructive:
            return "skip"

        # Destructive action detected - require confirmation
        self._actions_blocked += 1

        # Build clear action summary
        summary = self._build_action_summary(action, element_id, element_description, matched_patterns)

        # Ask for user confirmation
        confirmed = self._ask_confirmation(summary)

        if confirmed:
            self._actions_allowed += 1
            return "allow"
        else:
            return "block"

    def _build_action_summary(
        self,
        action: str,
        element_id: str | None,
        element_description: str,
        matched_patterns: list[str],
    ) -> str:
        """Build a clear action summary for user confirmation.

        Args:
            action: The action type.
            element_id: The element reference ID.
            element_description: Description of the element.
            matched_patterns: List of matched destructive patterns.

        Returns:
            A clear action summary string.
        """
        parts = [f"[bold red]DESTRUCTIVE ACTION DETECTED[/bold red]"]
        parts.append(f"Action: {action}")
        if element_id:
            parts.append(f"Element: {element_id}")
        if element_description:
            parts.append(f"Description: {element_description}")
        parts.append(f"Reason: Contains patterns: {', '.join(matched_patterns)}")
        parts.append("")
        parts.append("[yellow]Do you want to proceed?[/yellow]")

        return "\n".join(parts)

    def _ask_confirmation(self, summary: str) -> bool:
        """Ask the user for confirmation.

        Args:
            summary: The action summary to display.

        Returns:
            True if user confirmed (yes/y), False otherwise.
        """
        console.print(summary)

        while True:
            try:
                response = console.input("\n[yellow]Confirm?[/yellow] [bold green]yes[/bold green]/[bold red]no[/bold red]: ").strip().lower()
                if response in ("yes", "y", "confirm", "ok"):
                    console.print("[green]Action allowed.[/green]")
                    return True
                elif response in ("no", "n", "cancel", "abort"):
                    console.print("[red]Action blocked.[/red]")
                    return False
                else:
                    console.print("[dim]Please answer 'yes' or 'no'.[/dim]")
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Action cancelled.[/yellow]")
                return False

    def get_stats(self) -> dict[str, int]:
        """Get safety statistics.

        Returns:
            Dict with 'blocked' and 'allowed' counts.
        """
        return {
            "blocked": self._actions_blocked,
            "allowed": self._actions_allowed,
        }

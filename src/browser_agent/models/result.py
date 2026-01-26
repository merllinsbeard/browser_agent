"""Action result models for browser automation.

This module defines the ActionResult model which represents
the result of executing a browser action.
"""

from dataclasses import dataclass

from browser_agent.models.snapshot import PageSnapshot


@dataclass(frozen=True)
class ActionResult:
    """Result of executing a browser action.

    This represents the outcome of an action tool execution, including
    success status, a message describing what happened, and optionally
    a new page snapshot if the action changed the page state.

    Attributes:
        success: Whether the action executed successfully.
        message: Human-readable message describing the result.
        new_snapshot: New page snapshot after the action (if state changed).
        error: Error message if the action failed (None if success).
    """

    success: bool
    message: str
    new_snapshot: PageSnapshot | None = None
    error: str | None = None

    @staticmethod
    def success_result(message: str, new_snapshot: PageSnapshot | None = None) -> "ActionResult":
        """Create a successful action result."""
        return ActionResult(
            success=True,
            message=message,
            new_snapshot=new_snapshot,
            error=None,
        )

    @staticmethod
    def failure_result(message: str, error: str | None = None) -> "ActionResult":
        """Create a failed action result."""
        return ActionResult(
            success=False,
            message=message,
            new_snapshot=None,
            error=error or message,
        )

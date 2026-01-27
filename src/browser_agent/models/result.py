"""Action result models for browser automation.

This module defines the ActionResult type which represents
the result of executing a browser action.

The union type design makes invalid states unrepresentable:
- SuccessResult: always has message, never has error
- FailureResult: always has message and error
"""

from typing import Union

from pydantic import BaseModel, ConfigDict

from browser_agent.models.snapshot import PageSnapshot


class SuccessResult(BaseModel):
    """Result of a successful action execution.

    This represents a successful action outcome. By design,
    this type can never have an error - invalid states are
    unrepresentable.

    Attributes:
        message: Human-readable message describing the result.
        new_snapshot: New page snapshot after the action (if state changed).
    """

    model_config = ConfigDict(frozen=True)

    message: str
    new_snapshot: PageSnapshot | None = None

    @property
    def success(self) -> bool:
        """Always True for SuccessResult."""
        return True

    @property
    def error(self) -> None:
        """Always None for SuccessResult."""
        return None


class FailureResult(BaseModel):
    """Result of a failed action execution.

    This represents a failed action outcome. By design,
    this type always has both a message and an error.

    Attributes:
        message: Human-readable message describing the result.
        error: Error message describing the failure.
    """

    model_config = ConfigDict(frozen=True)

    message: str
    error: str

    @property
    def success(self) -> bool:
        """Always False for FailureResult."""
        return False

    @property
    def new_snapshot(self) -> None:
        """Always None for FailureResult."""
        return None


# Union type for action results
ActionResult = Union[SuccessResult, FailureResult]


def success_result(message: str, new_snapshot: PageSnapshot | None = None) -> ActionResult:
    """Create a successful action result.

    Args:
        message: Human-readable message describing the result.
        new_snapshot: New page snapshot after the action (if state changed).

    Returns:
        A SuccessResult instance.
    """
    return SuccessResult(message=message, new_snapshot=new_snapshot)


def failure_result(message: str, error: str | None = None) -> ActionResult:
    """Create a failed action result.

    Args:
        message: Human-readable message describing the result.
        error: Error message if the action failed (defaults to message).

    Returns:
        A FailureResult instance.
    """
    return FailureResult(message=message, error=error or message)

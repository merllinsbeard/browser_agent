"""Browser Agent data models."""

from browser_agent.models.element import BoundingBox, InteractiveElement
from browser_agent.models.result import (
    ActionResult,
    FailureResult,
    SuccessResult,
    failure_result,
    success_result,
)
from browser_agent.models.snapshot import PageSnapshot

__all__ = [
    "ActionResult",
    "BoundingBox",
    "FailureResult",
    "InteractiveElement",
    "PageSnapshot",
    "SuccessResult",
    "failure_result",
    "success_result",
]

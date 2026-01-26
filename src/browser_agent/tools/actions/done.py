"""Done action tool for browser automation.

This module provides the done function for signaling task completion.
"""

from browser_agent.models.result import ActionResult, success_result


def done(summary: str) -> ActionResult:
    """Signal task completion with a summary.

    Args:
        summary: A summary of what was accomplished.

    Returns:
        ActionResult indicating task completion with the summary.

    Note:
        This function should be called when the agent has successfully
        completed the user's task. The summary will be displayed to the user.
    """
    return success_result(
        message=f"Task completed: {summary}"
    )

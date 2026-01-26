"""Navigator agent for executing browser actions.

This module provides the Navigator agent which executes browser actions
according to a plan.
"""

from playwright.sync_api import Page

from browser_agent.core.registry import ElementRegistry
from browser_agent.models.result import ActionResult
from browser_agent.tools.actions import (
    click,
    done,
    extract,
    navigate,
    press,
    scroll,
    type_,
    wait,
)
from browser_agent.tools.observe import browser_observe


class NavigatorAgent:
    """Agent for executing browser actions.

    The Navigator receives plan steps and executes them sequentially,
    observing the page before each action and returning results.
    """

    def __init__(
        self,
        page: Page,
        registry: ElementRegistry,
        model: str | None = None,
    ) -> None:
        """Initialize the Navigator agent.

        Args:
            page: The Playwright Page object.
            registry: The ElementRegistry for element references.
            model: Model name to use for LLM calls (if needed).
        """
        self._page = page
        self._registry = registry
        self._model = model
        self._actions_completed = 0

    def execute_step(self, step_description: str) -> ActionResult:
        """Execute a single step from the plan.

        Args:
            step_description: A natural language description of the step.

        Returns:
            ActionResult indicating success or failure.
        """
        # Observe the page before acting
        snapshot = browser_observe(self._page, self._registry)

        # Parse the step to determine the action
        # This is a simplified implementation - in production, the LLM would parse
        parts = step_description.upper().split()

        try:
            if parts[0] == "NAVIGATE":
                # Extract URL from the step
                url = self._extract_url(step_description)
                if url:
                    result = navigate(self._page, url)
                    if result.success:
                        self._registry.increment_version()
                    return result
                else:
                    return ActionResult.failure_result(
                        f"Could not extract URL from: {step_description}"
                    )

            elif parts[0] == "CLICK":
                elem_id = self._extract_element_id(step_description)
                if elem_id:
                    return click(self._page, self._registry, elem_id)
                return ActionResult.failure_result(f"No element ID found in: {step_description}")

            elif parts[0] == "TYPE":
                elem_id = self._extract_element_id(step_description)
                text = self._extract_text_to_type(step_description)
                if elem_id and text:
                    result = type_(self._page, self._registry, elem_id, text)
                    assert isinstance(result, ActionResult)  # Type guard
                    return result
                return ActionResult.failure_result(f"Missing element ID or text in: {step_description}")

            elif parts[0] == "PRESS":
                key = self._extract_key(step_description)
                if key:
                    return press(self._page, key)
                return ActionResult.failure_result(f"No key found in: {step_description}")

            elif parts[0] == "SCROLL":
                return scroll(self._page)

            elif parts[0] == "WAIT":
                return wait(self._page)

            elif parts[0] == "EXTRACT":
                target = self._extract_target(step_description)
                return extract(self._page, target)

            elif parts[0] == "DONE":
                summary = self._extract_summary(step_description)
                self._actions_completed += 1
                return done(summary)

            else:
                return ActionResult.failure_result(
                    f"Unknown action in step: {step_description}"
                )

        except Exception as e:
            return ActionResult.failure_result(
                f"Error executing step: {step_description}",
                error=str(e),
            )

    def _extract_url(self, step: str) -> str | None:
        """Extract URL from a NAVIGATE step."""
        # Simple extraction - look for http/https URLs
        import re

        match = re.search(r'https?://\S+', step)
        return match.group(0) if match else None

    def _extract_element_id(self, step: str) -> str | None:
        """Extract element ID from a step."""
        import re

        match = re.search(r'elem-\d+', step)
        return match.group(0) if match else None

    def _extract_text_to_type(self, step: str) -> str | None:
        """Extract text to type from a TYPE step."""
        # Look for text after "TYPE" or in quotes
        parts = step.split()
        if len(parts) > 2:
            return " ".join(parts[2:]).strip('"\'')
        return None

    def _extract_key(self, step: str) -> str | None:
        """Extract key name from a PRESS step."""
        parts = step.split()
        if len(parts) > 1:
            return parts[1].upper()
        return None

    def _extract_target(self, step: str) -> str:
        """Extract target from an EXTRACT step."""
        return step.replace("EXTRACT", "").strip() or "page content"

    def _extract_summary(self, step: str) -> str:
        """Extract summary from a DONE step."""
        return step.replace("DONE", "").strip() or "Task completed"

    def get_actions_completed(self) -> int:
        """Get the number of actions completed.

        Returns:
            The count of completed actions.
        """
        return self._actions_completed

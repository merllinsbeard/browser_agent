"""Planner agent for breaking tasks into steps.

This module provides the Planner agent which creates execution plans
for browser automation tasks.
"""

from typing import Any

from browser_agent.core.llm import call_llm


class PlannerAgent:
    """Agent for creating execution plans from user tasks.

    The Planner receives a user's natural language task and creates
    a step-by-step execution plan. It maintains URL history for backtracking.
    """

    def __init__(self, model: str | None = None) -> None:
        """Initialize the Planner agent.

        Args:
            model: Model name to use for LLM calls. If None, uses default.
        """
        self._model = model
        self._url_history: list[str] = []
        self._plan: list[str] = []

    def create_plan(self, task: str, current_url: str = "") -> list[str]:
        """Create an execution plan for the given task.

        Args:
            task: The user's natural language task description.
            current_url: The current page URL (for context).

        Returns:
            A list of step descriptions representing the execution plan.
        """
        # Build context message with current state
        history_context = ""
        if self._url_history:
            history_context = f"\nRecent URLs visited: {self._url_history[-5:]}"
        if current_url:
            history_context += f"\nCurrent URL: {current_url}"

        system_prompt = """You are a browser automation planner. Your job is to break down a user's task into clear, actionable steps.

You have access to these browser actions:
- CLICK {element_id} - Click an interactive element
- TYPE {element_id} {text} - Type text into an input element
- PRESS {key} - Press a keyboard key (Enter, Escape, etc.)
- SCROLL {dx} {dy} - Scroll the page
- NAVIGATE {url} - Navigate to a URL
- WAIT {timeout_ms} - Wait for a specified time
- EXTRACT {target} - Extract data from the page
- DONE {summary} - Signal task completion

Important rules:
1. Start by navigating to the starting URL if not already there
2. Each step should be a single, clear action
3. Use element references like "elem-0", "elem-1" (from page observation)
4. Be specific about what you're looking for
5. End with DONE when the task is complete

Return your plan as a numbered list of steps, one per line."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Task: {task}{history_context}"},
        ]

        response = call_llm(messages, model=self._model)

        # Parse the response into a plan
        plan = self._parse_plan(response)
        self._plan = plan
        return plan

    def _parse_plan(self, response: str) -> list[str]:
        """Parse the LLM response into a list of steps.

        Args:
            response: The LLM's response text.

        Returns:
            A list of step descriptions.
        """
        lines = response.strip().split("\n")
        steps = []
        for line in lines:
            line = line.strip()
            # Skip empty lines and non-step lines
            if not line or not any(line.startswith(prefix) for prefix in ("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.", "-", "*")):
                continue
            # Remove numbering/bullets
            for prefix in ("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.", "- ", "* "):
                if line.startswith(prefix):
                    line = line[len(prefix) :].strip()
                    break
            if line:
                steps.append(line)
        return steps

    def add_url_to_history(self, url: str) -> None:
        """Add a URL to the navigation history.

        Args:
            url: The URL to add.
        """
        if url and url not in self._url_history:
            self._url_history.append(url)

    def get_current_plan(self) -> list[str]:
        """Get the current execution plan.

        Returns:
            The current list of steps in the plan.
        """
        return self._plan.copy()

    def clear_plan(self) -> None:
        """Clear the current plan."""
        self._plan = []

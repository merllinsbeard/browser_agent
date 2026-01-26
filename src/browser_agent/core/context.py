"""Context management module for token budget control.

This module provides context tracking and management to prevent token bloat
during agent execution.
"""

from browser_agent.models.snapshot import PageSnapshot


class ContextTracker:
    """Tracks and manages context to prevent token bloat.

    Implements single-snapshot retention: only the most recent snapshot
    is kept in context, with older snapshots being discarded.
    """

    def __init__(self, max_history_length: int = 50) -> None:
        """Initialize the context tracker.

        Args:
            max_history_length: Maximum number of history entries to keep.
                               Default is 50.
        """
        self._max_history_length = max_history_length
        self._current_snapshot: PageSnapshot | None = None
        self._action_history: list[dict[str, str | bool]] = []
        self._total_llm_calls: int = 0
        self._total_tokens_used: int = 0

    def update_snapshot(self, snapshot: PageSnapshot) -> PageSnapshot | None:
        """Update the current snapshot, discarding the old one.

        Args:
            snapshot: The new PageSnapshot to set as current.

        Returns:
            The previous snapshot if one existed, None otherwise.
        """
        previous = self._current_snapshot
        self._current_snapshot = snapshot
        return previous

    def get_current_snapshot(self) -> PageSnapshot | None:
        """Get the current snapshot.

        Returns:
            The most recent PageSnapshot, or None if none set.
        """
        return self._current_snapshot

    def record_action(
        self,
        action_type: str,
        success: bool,
        message: str = "",
    ) -> None:
        """Record an action in the history.

        Args:
            action_type: The type of action (e.g., "CLICK", "NAVIGATE").
            success: Whether the action succeeded.
            message: Optional message describing the result.
        """
        entry: dict[str, str | bool] = {
            "action": action_type,
            "success": success,
            "message": message,
        }

        self._action_history.append(entry)

        # Trim history if it exceeds max length
        if len(self._action_history) > self._max_history_length:
            self._action_history = self._action_history[-self._max_history_length :]

    def get_action_history(self) -> list[dict[str, str | bool]]:
        """Get the action history.

        Returns:
            A list of action history entries (most recent first).
        """
        return list(reversed(self._action_history))

    def get_recent_actions(self, count: int = 10) -> list[dict[str, str | bool]]:
        """Get the most recent actions.

        Args:
            count: Number of recent actions to return. Default is 10.

        Returns:
            A list of the most recent action history entries.
        """
        history = self.get_action_history()
        return history[:count]

    def record_llm_call(self, tokens_used: int = 0) -> None:
        """Record an LLM call for token tracking.

        Args:
            tokens_used: Estimated tokens used in this call.
        """
        self._total_llm_calls += 1
        self._total_tokens_used += tokens_used

    def get_llm_call_count(self) -> int:
        """Get the total number of LLM calls made.

        Returns:
            Total LLM calls count.
        """
        return self._total_llm_calls

    def get_total_tokens_used(self) -> int:
        """Get the total estimated tokens used.

        Returns:
            Total tokens used across all LLM calls.
        """
        return self._total_tokens_used

    def get_context_summary(self) -> dict[str, int | str]:
        """Get a summary of the current context state.

        Returns:
            A dictionary with context statistics.
        """
        return {
            "llm_calls": self._total_llm_calls,
            "total_tokens": self._total_tokens_used,
            "history_entries": len(self._action_history),
            "has_snapshot": self._current_snapshot is not None,
            "snapshot_version": (
                self._current_snapshot.version
                if self._current_snapshot
                else 0
            ),
        }

    def reset(self) -> None:
        """Reset the context tracker state."""
        self._current_snapshot = None
        self._action_history = []
        self._total_llm_calls = 0
        self._total_tokens_used = 0

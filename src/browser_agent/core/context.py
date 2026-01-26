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

    def __init__(
        self,
        max_history_length: int = 50,
        compression_interval: int = 10,
        llm_call_limit: int = 30,
    ) -> None:
        """Initialize the context tracker.

        Args:
            max_history_length: Maximum number of history entries to keep.
                               Default is 50.
            compression_interval: Compress history after this many steps.
                                 Default is 10.
            llm_call_limit: Alert when approaching this many LLM calls.
                            Default is 30.
        """
        self._max_history_length = max_history_length
        self._compression_interval = compression_interval
        self._llm_call_limit = llm_call_limit
        self._current_snapshot: PageSnapshot | None = None
        self._action_history: list[dict[str, str | bool]] = []
        self._total_llm_calls: int = 0
        self._total_tokens_used: int = 0
        self._compressed_summary: str = ""
        self._tokens_by_category: dict[str, int] = {
            "snapshot": 0,
            "history": 0,
            "tools": 0,
            "other": 0,
        }

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

    def record_llm_call(
        self,
        tokens_used: int = 0,
        category: str = "other",
    ) -> None:
        """Record an LLM call for token tracking.

        Args:
            tokens_used: Estimated tokens used in this call.
            category: Token category (snapshot, history, tools, other).
                      Default is "other".
        """
        self._total_llm_calls += 1
        self._total_tokens_used += tokens_used

        # Track by category
        if category in self._tokens_by_category:
            self._tokens_by_category[category] += tokens_used
        else:
            self._tokens_by_category["other"] += tokens_used

    def track_tokens(
        self,
        category: str,
        tokens: int,
    ) -> None:
        """Track token usage by category.

        Args:
            category: Token category (snapshot, history, tools, other).
            tokens: Number of tokens to add to the category.
        """
        if category in self._tokens_by_category:
            self._tokens_by_category[category] += tokens
        else:
            self._tokens_by_category["other"] += tokens

    def get_tokens_by_category(self) -> dict[str, int]:
        """Get token usage breakdown by category.

        Returns:
            Dictionary with token counts per category.
        """
        return self._tokens_by_category.copy()

    def approaching_limit(self) -> bool:
        """Check if approaching LLM call limit.

        Returns:
            True if at 80% of the LLM call limit.
        """
        return self._total_llm_calls >= int(self._llm_call_limit * 0.8)

    def get_llm_call_limit(self) -> int:
        """Get the LLM call limit.

        Returns:
            The configured LLM call limit.
        """
        return self._llm_call_limit

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
            "llm_limit": self._llm_call_limit,
            "total_tokens": self._total_tokens_used,
            "tokens_snapshot": self._tokens_by_category.get("snapshot", 0),
            "tokens_history": self._tokens_by_category.get("history", 0),
            "tokens_tools": self._tokens_by_category.get("tools", 0),
            "tokens_other": self._tokens_by_category.get("other", 0),
            "history_entries": len(self._action_history),
            "has_snapshot": self._current_snapshot is not None,
            "snapshot_version": (
                self._current_snapshot.version
                if self._current_snapshot
                else 0
            ),
            "approaching_limit": self.approaching_limit(),
        }

    def reset(self) -> None:
        """Reset the context tracker state."""
        self._current_snapshot = None
        self._action_history = []
        self._total_llm_calls = 0
        self._total_tokens_used = 0
        self._compressed_summary = ""
        for key in self._tokens_by_category:
            self._tokens_by_category[key] = 0

    def should_compress(self) -> bool:
        """Check if task memory should be compressed.

        Returns:
            True if compression is needed (at compression_interval).
        """
        return len(self._action_history) >= self._compression_interval

    def compress_task_memory(
        self,
        current_url: str = "",
        current_task: str = "",
    ) -> str:
        """Compress task history to save tokens.

        Summarizes older steps and keeps recent steps detailed.
        Should be called every compression_interval steps.

        Args:
            current_url: The current page URL (for context).
            current_task: The current task description (for context).

        Returns:
            A compressed summary of completed steps and current state.
        """
        if len(self._action_history) == 0:
            return ""

        # Determine how many actions to keep in detail
        recent_count = min(5, len(self._action_history))
        total_count = len(self._action_history)

        # Generate summary from ALL actions
        summary_parts = []

        # Count actions by type across ALL history
        action_counts: dict[str, int] = {}
        successful_count = 0
        failed_count = 0

        for entry in self._action_history:
            action = entry.get("action")
            if isinstance(action, str):
                action_counts[action] = action_counts.get(action, 0) + 1
            success = entry.get("success")
            if isinstance(success, bool):
                if success:
                    successful_count += 1
                else:
                    failed_count += 1

        # Build summary
        summary_parts.append(f"Completed {total_count} actions:")

        # Add action breakdown
        if action_counts:
            action_summary = ", ".join(
                f"{count} {action.lower()}(s)"
                for action, count in sorted(action_counts.items())
            )
            summary_parts.append(f"  Actions: {action_summary}")

        # Add success rate
        if successful_count > 0 or failed_count > 0:
            total = successful_count + failed_count
            rate = (successful_count / total * 100) if total > 0 else 0
            summary_parts.append(
                f"  Success rate: {successful_count}/{total} ({rate:.0f}%)"
            )

        # Add current state
        summary_parts.append("\nCurrent state:")
        if current_url:
            summary_parts.append(f"  URL: {current_url}")
        if current_task:
            summary_parts.append(f"  Task: {current_task}")
        if self._current_snapshot:
            summary_parts.append(
                f"  Page: {self._current_snapshot.title or 'Untitled'}"
            )

        # Store the compressed summary
        self._compressed_summary = "\n".join(summary_parts)

        # Keep only recent history in detail
        if recent_count < total_count:
            self._action_history = self._action_history[-recent_count:]

        return self._compressed_summary

    def get_compressed_summary(self) -> str:
        """Get the current compressed summary.

        Returns:
            The compressed task memory summary, or empty string if none.
        """
        return self._compressed_summary

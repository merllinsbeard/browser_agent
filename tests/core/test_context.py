"""Tests for ContextTracker."""

import pytest

from browser_agent.core.context import ContextTracker
from browser_agent.models.element import BoundingBox, InteractiveElement
from browser_agent.models.snapshot import PageSnapshot


@pytest.fixture
def sample_snapshot():
    """Create a sample PageSnapshot for testing."""
    return PageSnapshot(
        url="https://example.com",
        title="Example Page",
        interactive_elements=[
            InteractiveElement(
                ref="elem-0",
                role="button",
                name="Submit",
                aria_label="Submit form",
                placeholder="",
                value_preview="",
                bbox=BoundingBox(x=0, y=0, width=100, height=40),
            ),
        ],
        visible_text_excerpt="Sample text content",
        screenshot_path="",
        notes="",
        version=1,
    )


def test_context_tracker_initialization():
    """Test that ContextTracker initializes with correct defaults."""
    tracker = ContextTracker()

    assert tracker._max_history_length == 50
    assert tracker._compression_interval == 10
    assert tracker._llm_call_limit == 30
    assert tracker._current_snapshot is None
    assert tracker._action_history == []
    assert tracker._total_llm_calls == 0
    assert tracker._total_tokens_used == 0
    assert tracker._compressed_summary == ""


def test_context_tracker_custom_initialization():
    """Test ContextTracker with custom parameters."""
    tracker = ContextTracker(
        max_history_length=100,
        compression_interval=20,
        llm_call_limit=50,
    )

    assert tracker._max_history_length == 100
    assert tracker._compression_interval == 20
    assert tracker._llm_call_limit == 50


def test_update_snapshot_returns_previous(sample_snapshot):
    """Test that update_snapshot returns the previous snapshot."""
    tracker = ContextTracker()

    # First update - no previous
    previous = tracker.update_snapshot(sample_snapshot)
    assert previous is None

    # Create a new snapshot
    new_snapshot = PageSnapshot(
        url="https://example.com/new",
        title="New Page",
        interactive_elements=[],
        visible_text_excerpt="",
        screenshot_path="",
        notes="",
        version=2,
    )

    # Second update - returns previous
    previous = tracker.update_snapshot(new_snapshot)
    assert previous == sample_snapshot


def test_update_snapshot_sets_current(sample_snapshot):
    """Test that update_snapshot sets the current snapshot."""
    tracker = ContextTracker()

    tracker.update_snapshot(sample_snapshot)

    assert tracker.get_current_snapshot() == sample_snapshot


def test_get_current_snapshot_returns_none_initially():
    """Test that get_current_snapshot returns None initially."""
    tracker = ContextTracker()

    assert tracker.get_current_snapshot() is None


def test_record_action_adds_to_history():
    """Test that record_action adds entries to history."""
    tracker = ContextTracker()

    tracker.record_action("CLICK", True, "Clicked button")
    tracker.record_action("NAVIGATE", False, "Navigation failed")

    history = tracker.get_action_history()

    assert len(history) == 2
    # History is reversed (most recent first)
    assert history[0]["action"] == "NAVIGATE"
    assert history[0]["success"] is False
    assert history[1]["action"] == "CLICK"
    assert history[1]["success"] is True


def test_record_action_trims_history():
    """Test that record_action trims history when exceeding max length."""
    tracker = ContextTracker(max_history_length=5)

    # Add 7 actions
    for i in range(7):
        tracker.record_action(f"ACTION_{i}", True, f"Action {i}")

    history = tracker.get_action_history()

    # Should only have 5 entries (most recent)
    assert len(history) == 5
    # Should have ACTION_6 through ACTION_2
    assert history[0]["action"] == "ACTION_6"
    assert history[4]["action"] == "ACTION_2"


def test_get_action_history_returns_reversed():
    """Test that get_action_history returns most recent first."""
    tracker = ContextTracker()

    tracker.record_action("ACTION_1", True)
    tracker.record_action("ACTION_2", True)
    tracker.record_action("ACTION_3", True)

    history = tracker.get_action_history()

    assert history[0]["action"] == "ACTION_3"
    assert history[1]["action"] == "ACTION_2"
    assert history[2]["action"] == "ACTION_1"


def test_get_recent_actions_limits_count():
    """Test that get_recent_actions limits the count."""
    tracker = ContextTracker()

    for i in range(10):
        tracker.record_action(f"ACTION_{i}", True)

    recent = tracker.get_recent_actions(3)

    assert len(recent) == 3
    assert recent[0]["action"] == "ACTION_9"
    assert recent[1]["action"] == "ACTION_8"
    assert recent[2]["action"] == "ACTION_7"


def test_get_recent_actions_default_count():
    """Test that get_recent_actions defaults to 10."""
    tracker = ContextTracker()

    for i in range(20):
        tracker.record_action(f"ACTION_{i}", True)

    recent = tracker.get_recent_actions()

    assert len(recent) == 10


def test_record_llm_call_tracks_calls_and_tokens():
    """Test that record_llm_call tracks calls and tokens."""
    tracker = ContextTracker()

    tracker.record_llm_call(tokens_used=100, category="snapshot")
    tracker.record_llm_call(tokens_used=200, category="tools")

    assert tracker.get_llm_call_count() == 2
    assert tracker.get_total_tokens_used() == 300


def test_record_llm_call_tracks_by_category():
    """Test that record_llm_call tracks tokens by category."""
    tracker = ContextTracker()

    tracker.record_llm_call(tokens_used=100, category="snapshot")
    tracker.record_llm_call(tokens_used=200, category="tools")
    tracker.record_llm_call(tokens_used=50, category="other")

    tokens = tracker.get_tokens_by_category()

    assert tokens["snapshot"] == 100
    assert tokens["tools"] == 200
    assert tokens["other"] == 50
    assert tokens["history"] == 0


def test_record_llm_call_unknown_category_maps_to_other():
    """Test that unknown categories map to 'other'."""
    tracker = ContextTracker()

    tracker.record_llm_call(tokens_used=100, category="unknown")

    tokens = tracker.get_tokens_by_category()

    assert tokens["other"] == 100


def test_track_tokens_adds_to_category():
    """Test that track_tokens adds tokens to a category."""
    tracker = ContextTracker()

    tracker.track_tokens("snapshot", 100)
    tracker.track_tokens("snapshot", 50)

    tokens = tracker.get_tokens_by_category()

    assert tokens["snapshot"] == 150


def test_track_tokens_unknown_category_maps_to_other():
    """Test that track_tokens maps unknown categories to 'other'."""
    tracker = ContextTracker()

    tracker.track_tokens("unknown", 100)

    tokens = tracker.get_tokens_by_category()

    assert tokens["other"] == 100


def test_approaching_limit_at_80_percent():
    """Test that approaching_limit returns True at 80% of limit."""
    tracker = ContextTracker(llm_call_limit=30)

    # 24 is 80% of 30
    for _ in range(24):
        tracker.record_llm_call()

    assert tracker.approaching_limit() is True


def test_approaching_limit_below_80_percent():
    """Test that approaching_limit returns False below 80%."""
    tracker = ContextTracker(llm_call_limit=30)

    # 23 is below 80% of 30
    for _ in range(23):
        tracker.record_llm_call()

    assert tracker.approaching_limit() is False


def test_get_llm_call_limit():
    """Test get_llm_call_limit returns configured limit."""
    tracker = ContextTracker(llm_call_limit=50)

    assert tracker.get_llm_call_limit() == 50


def test_get_llm_call_count():
    """Test get_llm_call_count returns total calls."""
    tracker = ContextTracker()

    tracker.record_llm_call()
    tracker.record_llm_call()
    tracker.record_llm_call()

    assert tracker.get_llm_call_count() == 3


def test_get_total_tokens_used():
    """Test get_total_tokens_used returns sum of all tokens."""
    tracker = ContextTracker()

    tracker.record_llm_call(tokens_used=100)
    tracker.record_llm_call(tokens_used=200)
    tracker.record_llm_call(tokens_used=50)

    assert tracker.get_total_tokens_used() == 350


def test_get_context_summary(sample_snapshot):
    """Test get_context_summary returns correct statistics."""
    tracker = ContextTracker(llm_call_limit=30)

    tracker.update_snapshot(sample_snapshot)
    tracker.record_action("CLICK", True, "Clicked button")
    tracker.record_action("NAVIGATE", True, "Navigated")
    tracker.record_llm_call(tokens_used=100, category="snapshot")

    summary = tracker.get_context_summary()

    assert summary["llm_calls"] == 1
    assert summary["llm_limit"] == 30
    assert summary["total_tokens"] == 100
    assert summary["tokens_snapshot"] == 100
    assert summary["tokens_history"] == 0
    assert summary["tokens_tools"] == 0
    assert summary["tokens_other"] == 0
    assert summary["history_entries"] == 2
    assert summary["has_snapshot"] is True
    assert summary["snapshot_version"] == 1
    assert summary["approaching_limit"] is False


def test_get_context_summary_no_snapshot():
    """Test get_context_summary when no snapshot is set."""
    tracker = ContextTracker()

    summary = tracker.get_context_summary()

    assert summary["has_snapshot"] is False
    assert summary["snapshot_version"] == 0


def test_reset_clears_all_state(sample_snapshot):
    """Test that reset clears all tracker state."""
    tracker = ContextTracker()

    tracker.update_snapshot(sample_snapshot)
    tracker.record_action("CLICK", True)
    tracker.record_llm_call(tokens_used=100, category="snapshot")
    tracker.track_tokens("tools", 50)

    tracker.reset()

    assert tracker.get_current_snapshot() is None
    assert tracker._action_history == []
    assert tracker._total_llm_calls == 0
    assert tracker._total_tokens_used == 0
    assert tracker._compressed_summary == ""
    assert tracker.get_tokens_by_category()["snapshot"] == 0
    assert tracker.get_tokens_by_category()["tools"] == 0


def test_should_compress_at_interval():
    """Test that should_compress returns True at compression interval."""
    tracker = ContextTracker(compression_interval=10)

    for _ in range(10):
        tracker.record_action("CLICK", True)

    assert tracker.should_compress() is True


def test_should_compress_below_interval():
    """Test that should_compress returns False below interval."""
    tracker = ContextTracker(compression_interval=10)

    for _ in range(9):
        tracker.record_action("CLICK", True)

    assert tracker.should_compress() is False


def test_compress_task_memory_returns_summary():
    """Test that compress_task_memory returns compressed summary."""
    tracker = ContextTracker()

    for i in range(15):
        tracker.record_action("CLICK", True)

    summary = tracker.compress_task_memory(
        current_url="https://example.com",
        current_task="Search for items",
    )

    assert "Completed 15 actions:" in summary
    assert "click" in summary.lower()
    assert "Success rate:" in summary
    assert "URL: https://example.com" in summary
    assert "Task: Search for items" in summary


def test_compress_task_memory_keeps_recent_actions():
    """Test that compress_task_memory keeps 5 most recent actions."""
    tracker = ContextTracker()

    for i in range(15):
        tracker.record_action(f"ACTION_{i}", True)

    tracker.compress_task_memory()

    history = tracker.get_action_history()

    # Should have 5 recent actions (ACTION_14 through ACTION_10)
    assert len(history) == 5
    assert history[0]["action"] == "ACTION_14"
    assert history[4]["action"] == "ACTION_10"


def test_compress_task_memory_with_snapshot(sample_snapshot):
    """Test that compress_task_memory includes page title from snapshot."""
    tracker = ContextTracker()

    tracker.update_snapshot(sample_snapshot)

    for i in range(15):
        tracker.record_action("CLICK", True)

    summary = tracker.compress_task_memory()

    assert "Page: Example Page" in summary


def test_compress_task_memory_empty_history():
    """Test that compress_task_memory returns empty string for empty history."""
    tracker = ContextTracker()

    summary = tracker.compress_task_memory()

    assert summary == ""


def test_compress_task_memory_counts_success_rate():
    """Test that compress_task_memory correctly calculates success rate."""
    tracker = ContextTracker()

    # 10 actions: 7 success, 3 failure
    for _ in range(7):
        tracker.record_action("CLICK", True)
    for _ in range(3):
        tracker.record_action("CLICK", False)

    summary = tracker.compress_task_memory()

    assert "Success rate: 7/10 (70%)" in summary


def test_get_compressed_summary():
    """Test get_compressed_summary returns the stored summary."""
    tracker = ContextTracker()

    for i in range(15):
        tracker.record_action("CLICK", True)

    tracker.compress_task_memory(current_url="https://example.com")
    summary = tracker.get_compressed_summary()

    assert "Completed 15 actions:" in summary
    assert "https://example.com" in summary


def test_get_compressed_summary_initially_empty():
    """Test that get_compressed_summary returns empty string initially."""
    tracker = ContextTracker()

    assert tracker.get_compressed_summary() == ""


def test_full_compression_cycle():
    """Test a full compression cycle with URL and task."""
    tracker = ContextTracker(compression_interval=5, llm_call_limit=10)

    # Record some actions
    tracker.record_action("NAVIGATE", True, "Navigated to home")
    tracker.record_action("CLICK", True, "Clicked search")
    tracker.record_action("TYPE", True, "Typed query")
    tracker.record_action("PRESS", True, "Pressed Enter")
    tracker.record_action("WAIT", True, "Waited for results")

    # Should need compression
    assert tracker.should_compress() is True

    # Compress
    summary = tracker.compress_task_memory(
        current_url="https://example.com/search",
        current_task="Search for products",
    )

    # Should have summary
    assert "Completed 5 actions:" in summary
    assert "URL: https://example.com/search" in summary
    assert "Task: Search for products" in summary

    # Recent actions should be preserved
    recent = tracker.get_recent_actions(5)
    assert len(recent) == 5

    # Summary should be retrievable
    assert tracker.get_compressed_summary() == summary


def test_token_tracking_across_categories():
    """Test token tracking across multiple categories."""
    tracker = ContextTracker()

    tracker.track_tokens("snapshot", 1000)
    tracker.track_tokens("history", 500)
    tracker.track_tokens("tools", 300)
    tracker.track_tokens("other", 200)

    tokens = tracker.get_tokens_by_category()

    assert tokens["snapshot"] == 1000
    assert tokens["history"] == 500
    assert tokens["tools"] == 300
    assert tokens["other"] == 200

    # Total should be sum
    assert tracker.get_total_tokens_used() == 0  # track_tokens doesn't add to total

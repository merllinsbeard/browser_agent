"""Tests for Action enum."""

from browser_agent.models.action import Action


def test_action_click_value() -> None:
    """Test Action.CLICK has correct value."""
    assert Action.CLICK == "CLICK"


def test_action_type_value() -> None:
    """Test Action.TYPE has correct value."""
    assert Action.TYPE == "TYPE"


def test_action_press_value() -> None:
    """Test Action.PRESS has correct value."""
    assert Action.PRESS == "PRESS"


def test_action_scroll_value() -> None:
    """Test Action.SCROLL has correct value."""
    assert Action.SCROLL == "SCROLL"


def test_action_navigate_value() -> None:
    """Test Action.NAVIGATE has correct value."""
    assert Action.NAVIGATE == "NAVIGATE"


def test_action_wait_value() -> None:
    """Test Action.WAIT has correct value."""
    assert Action.WAIT == "WAIT"


def test_action_extract_value() -> None:
    """Test Action.EXTRACT has correct value."""
    assert Action.EXTRACT == "EXTRACT"


def test_action_done_value() -> None:
    """Test Action.DONE has correct value."""
    assert Action.DONE == "DONE"


def test_action_is_string() -> None:
    """Test Action values can be compared with strings."""
    assert Action.CLICK == "CLICK"
    assert "CLICK" == Action.CLICK


def test_action_iteration() -> None:
    """Test all Action enum values can be iterated."""
    actions = list(Action)
    assert len(actions) == 8
    assert Action.CLICK in actions
    assert Action.DONE in actions

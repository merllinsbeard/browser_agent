"""Tests for browser action tools."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from browser_agent.core.registry import ElementRegistry, StaleElementError
from browser_agent.models.result import ActionResult
from browser_agent.tools.actions import (
    click,
    press,
    scroll,
    navigate,
    wait,
    extract,
    done,
)
# Import type_ separately to avoid import conflicts
from browser_agent.tools.actions.type import type_


@pytest.fixture
def mock_page():
    """Create a mock Playwright Page object."""
    page = MagicMock()
    page.url = "https://example.com"
    page.keyboard = MagicMock()
    page.evaluate = MagicMock()
    page.goto = MagicMock()
    page.wait_for_timeout = MagicMock()
    page.locator = MagicMock()
    return page


@pytest.fixture
def mock_registry():
    """Create a mock ElementRegistry."""
    registry = MagicMock(spec=ElementRegistry)
    return registry


@pytest.fixture
def mock_locator():
    """Create a mock Playwright Locator."""
    locator = MagicMock()
    locator.click = MagicMock()
    locator.fill = MagicMock()
    locator.count = MagicMock(return_value=1)
    return locator


def test_click_success(mock_page: MagicMock, mock_registry: MagicMock, mock_locator: MagicMock) -> None:
    """Test successful click action."""
    mock_registry.get_locator.return_value = mock_locator

    result = click(mock_page, mock_registry, "elem-0")

    assert result.success is True
    assert "clicked" in result.message.lower()
    mock_locator.click.assert_called_once()


def test_click_stale_element(mock_page: MagicMock, mock_registry: MagicMock) -> None:
    """Test click with stale element reference."""
    mock_registry.get_locator.side_effect = StaleElementError("elem-0", 1, 2)

    result = click(mock_page, mock_registry, "elem-0")

    assert result.success is False
    assert "stale" in result.error.lower()


def test_click_timeout(mock_page: MagicMock, mock_registry: MagicMock, mock_locator: MagicMock) -> None:
    """Test click with timeout error."""
    mock_registry.get_locator.return_value = mock_locator
    mock_locator.click.side_effect = PlaywrightTimeoutError("Timeout")

    result = click(mock_page, mock_registry, "elem-0")

    assert result.success is False
    assert "timeout" in result.error.lower()


def test_type_success(mock_page: MagicMock, mock_registry: MagicMock, mock_locator: MagicMock) -> None:
    """Test successful type action."""
    mock_registry.get_locator.return_value = mock_locator

    result = type_(mock_page, mock_registry, "elem-0", "test text")

    assert result.success is True
    assert "typed" in result.message.lower() or "fill" in result.message.lower()
    mock_locator.fill.assert_called_once_with("test text")


def test_press_success(mock_page: MagicMock) -> None:
    """Test successful press action."""
    result = press(mock_page, "Enter")

    assert result.success is True
    mock_page.keyboard.press.assert_called_once_with("Enter")


def test_press_combination(mock_page: MagicMock) -> None:
    """Test press with key combination."""
    result = press(mock_page, "Control+A")

    assert result.success is True
    mock_page.keyboard.press.assert_called_once_with("Control+A")


def test_scroll_success(mock_page: MagicMock) -> None:
    """Test successful scroll action."""
    mock_page.evaluate.return_value = None

    result = scroll(mock_page, dx=100, dy=200)

    assert result.success is True
    assert "scroll" in result.message.lower()
    mock_page.evaluate.assert_called_once()


def test_navigate_success(mock_page: MagicMock) -> None:
    """Test successful navigate action."""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_page.goto.return_value = mock_response

    result = navigate(mock_page, "https://example.com")

    assert result.success is True
    assert "200" in result.message
    mock_page.goto.assert_called_once()


def test_navigate_redirect(mock_page: MagicMock) -> None:
    """Test navigate with redirect (3xx status)."""
    mock_response = MagicMock()
    mock_response.status = 301
    mock_page.goto.return_value = mock_response

    result = navigate(mock_page, "https://example.com")

    assert result.success is True
    assert "301" in result.message


def test_navigate_error(mock_page: MagicMock) -> None:
    """Test navigate with error status."""
    mock_response = MagicMock()
    mock_response.status = 404
    mock_page.goto.return_value = mock_response

    result = navigate(mock_page, "https://example.com")

    assert result.success is False
    assert "404" in result.message


def test_wait_success(mock_page: MagicMock) -> None:
    """Test successful wait action."""
    result = wait(mock_page, 1000)

    assert result.success is True
    assert "1000" in result.message
    mock_page.wait_for_timeout.assert_called_once_with(1000)


def test_extract_title(mock_page: MagicMock) -> None:
    """Test extract action for title."""
    mock_page.title = "Test Page"

    result = extract(mock_page, "title")

    assert result.success is True
    assert "Test Page" in result.message


def test_extract_url(mock_page: MagicMock) -> None:
    """Test extract action for URL."""
    mock_page.url = "https://example.com/page"

    result = extract(mock_page, "url")

    assert result.success is True
    assert "https://example.com/page" in result.message


def test_done_success() -> None:
    """Test done action."""
    result = done("Task completed successfully")

    assert result.success is True
    assert "completed" in result.message.lower()

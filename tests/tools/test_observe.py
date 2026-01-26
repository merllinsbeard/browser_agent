"""Tests for browser observation tools."""

from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

from browser_agent.core.registry import ElementRegistry
from browser_agent.models.snapshot import PageSnapshot
from browser_agent.tools.observe import browser_observe, _extract_interactive_elements


@pytest.fixture
def mock_page():
    """Create a mock Playwright Page object."""
    page = MagicMock()
    page.locator = MagicMock()
    page.url = "https://example.com"
    page.title = "Example Page"
    return page


@pytest.fixture
def sample_aria_yaml() -> str:
    """Sample ARIA snapshot YAML for testing."""
    return """
- role: link
  name: "Home"
  url: "https://example.com/"
- role: link
  name: "About"
  url: "https://example.com/about"
- role: textbox
  name: "Search"
  description: "Search box"
- role: button
  name: "Submit"
  description: "Submit form"
"""


def test_browser_observe_returns_snapshot(
    mock_page: MagicMock,
    sample_aria_yaml: str,
) -> None:
    """Test that browser_observe returns a PageSnapshot."""
    mock_page.locator.return_value.aria_snapshot.return_value = sample_aria_yaml

    registry = ElementRegistry()
    snapshot = browser_observe(mock_page, registry)

    assert isinstance(snapshot, PageSnapshot)
    assert snapshot.url == "https://example.com"
    assert snapshot.title == "Example Page"
    assert len(snapshot.interactive_elements) > 0
    assert snapshot.version >= 0


def test_browser_observe_registers_elements(
    mock_page: MagicMock,
    sample_aria_yaml: str,
) -> None:
    """Test that browser_observe registers elements in the registry."""
    mock_page.locator.return_value.aria_snapshot.return_value = sample_aria_yaml

    registry = ElementRegistry()
    snapshot = browser_observe(mock_page, registry)

    # Should have registered some elements
    assert len(snapshot.interactive_elements) > 0

    # Check that elements have ref IDs
    for elem in snapshot.interactive_elements:
        assert elem.ref.startswith("elem-")


def test_browser_observe_limits_elements(
    mock_page: MagicMock,
    sample_aria_yaml: str,
) -> None:
    """Test that browser_observe respects max_elements parameter."""
    mock_page.locator.return_value.aria_snapshot.return_value = sample_aria_yaml

    registry = ElementRegistry()
    snapshot = browser_observe(mock_page, registry, max_elements=2)

    # Should limit to 2 elements
    assert len(snapshot.interactive_elements) <= 2


def test_browser_observe_includes_screenshot_path(
    mock_page: MagicMock,
    sample_aria_yaml: str,
    tmp_path: Path,
) -> None:
    """Test that browser_observe includes screenshot path when provided."""
    mock_page.locator.return_value.aria_snapshot.return_value = sample_aria_yaml

    registry = ElementRegistry()
    screenshot_path = tmp_path / "test_screenshot.png"

    snapshot = browser_observe(
        mock_page,
        registry,
        screenshot_path=screenshot_path,
    )

    assert snapshot.screenshot_path == screenshot_path


def test_extract_interactive_elements_parses_yaml() -> None:
    """Test that _extract_interactive_elements parses ARIA YAML correctly."""
    yaml = """
- role: link
  name: "Home"
- role: button
  name: "Click Me"
"""

    elements = _extract_interactive_elements(yaml, max_elements=10)

    assert len(elements) == 2
    assert elements[0].role == "link"
    assert elements[0].name == "Home"
    assert elements[1].role == "button"
    assert elements[1].name == "Click Me"


def test_extract_interactive_elements_respects_max_elements() -> None:
    """Test that _extract_interactive_elements respects max_elements limit."""
    yaml = """
- role: link
  name: "Link 1"
- role: link
  name: "Link 2"
- role: link
  name: "Link 3"
"""

    elements = _extract_interactive_elements(yaml, max_elements=2)

    assert len(elements) == 2

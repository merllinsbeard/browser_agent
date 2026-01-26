"""Tests for screenshot capture tool."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from browser_agent.tools.screenshot import capture_screenshot


@pytest.fixture
def mock_page():
    """Create a mock Playwright Page object."""
    page = MagicMock()

    def mock_screenshot_impl(path: str, **kwargs):
        """Mock implementation that actually creates the file."""
        Path(path).write_bytes(b"fake_png_data")
        return None

    page.screenshot = MagicMock(side_effect=mock_screenshot_impl)
    return page


def test_capture_screenshot_creates_file(mock_page: MagicMock, tmp_path: Path) -> None:
    """Test that capture_screenshot creates a file."""
    output_path = tmp_path / "screenshot.png"
    result = capture_screenshot(mock_page, output_path=output_path)

    assert result.exists()
    assert result.suffix == ".png"
    mock_page.screenshot.assert_called_once()


def test_capture_screenshot_auto_name(mock_page: MagicMock, tmp_path: Path) -> None:
    """Test that capture_screenshot generates timestamped filename when no path provided."""
    result = capture_screenshot(mock_page)

    assert result.exists()
    assert result.name.startswith("screenshot-")
    assert result.suffix == ".png"


def test_capture_screenshot_creates_parent_dirs(mock_page: MagicMock, tmp_path: Path) -> None:
    """Test that capture_screenshot creates parent directories."""
    output_path = tmp_path / "subdir" / "nested" / "screenshot.png"
    result = capture_screenshot(mock_page, output_path=output_path)

    assert result.exists()
    assert result.parent.exists()


def test_capture_screenshot_full_page(mock_page: MagicMock, tmp_path: Path) -> None:
    """Test that capture_screenshot respects full_page parameter."""
    output_path = tmp_path / "screenshot.png"
    capture_screenshot(mock_page, output_path=output_path, full_page=True)

    # Check that full_page=True was passed
    call_kwargs = mock_page.screenshot.call_args[1] if mock_page.screenshot.call_args[1] else {}
    assert call_kwargs.get("full_page") is True


def test_capture_screenshot_viewport(mock_page: MagicMock, tmp_path: Path) -> None:
    """Test that capture_screenshot defaults to viewport only."""
    output_path = tmp_path / "screenshot.png"
    capture_screenshot(mock_page, output_path=output_path, full_page=False)

    # Check that full_page=False was passed
    call_kwargs = mock_page.screenshot.call_args[1] if mock_page.screenshot.call_args[1] else {}
    assert call_kwargs.get("full_page") is False

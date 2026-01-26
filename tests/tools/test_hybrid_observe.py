"""Tests for hybrid observation tool with screenshot fallback."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from browser_agent.core.registry import ElementRegistry
from browser_agent.models.snapshot import PageSnapshot
from browser_agent.tools.hybrid_observe import (
    hybrid_observe,
    invoke_vision_model,
    needs_vision_fallback,
)


@pytest.fixture
def mock_page() -> MagicMock:
    """Create a mock Playwright Page object."""
    page = MagicMock()
    page.url = "https://example.com"
    page.title = "Test Page"
    return page


@pytest.fixture
def mock_registry() -> MagicMock:
    """Create a mock ElementRegistry."""
    return MagicMock(spec=ElementRegistry)


@pytest.fixture
def mock_snapshot() -> MagicMock:
    """Create a mock PageSnapshot with few elements."""
    snapshot = MagicMock(spec=PageSnapshot)
    snapshot.interactive_elements = []
    return snapshot


def test_needs_vision_fallback_below_threshold(mock_snapshot: MagicMock) -> None:
    """Test vision fallback is needed when element count is below threshold."""
    mock_snapshot.interactive_elements = [MagicMock() for _ in range(5)]

    result = needs_vision_fallback(mock_snapshot, threshold=10)

    assert result is True


def test_needs_vision_fallback_at_threshold(mock_snapshot: MagicMock) -> None:
    """Test vision fallback is not needed when element count equals threshold."""
    mock_snapshot.interactive_elements = [MagicMock() for _ in range(10)]

    result = needs_vision_fallback(mock_snapshot, threshold=10)

    assert result is False


def test_needs_vision_fallback_above_threshold(mock_snapshot: MagicMock) -> None:
    """Test vision fallback is not needed when element count exceeds threshold."""
    mock_snapshot.interactive_elements = [MagicMock() for _ in range(20)]

    result = needs_vision_fallback(mock_snapshot, threshold=10)

    assert result is False


def test_needs_vision_fallback_custom_threshold(mock_snapshot: MagicMock) -> None:
    """Test vision fallback with custom threshold."""
    mock_snapshot.interactive_elements = [MagicMock() for _ in range(3)]

    result = needs_vision_fallback(mock_snapshot, threshold=5)

    assert result is True


def test_needs_vision_fallback_empty_elements(mock_snapshot: MagicMock) -> None:
    """Test vision fallback with no elements."""
    mock_snapshot.interactive_elements = []

    result = needs_vision_fallback(mock_snapshot, threshold=10)

    assert result is True


@patch("browser_agent.tools.hybrid_observe.capture_screenshot")
@patch("browser_agent.tools.hybrid_observe.observe")
def test_hybrid_observe_captures_screenshot(
    mock_observe: MagicMock,
    mock_capture_screenshot: MagicMock,
    mock_page: MagicMock,
    mock_registry: MagicMock,
) -> None:
    """Test hybrid_observe captures screenshot before observation."""
    mock_capture_screenshot.return_value = Path("/tmp/screenshot.png")
    mock_snapshot = MagicMock(spec=PageSnapshot)
    mock_observe.browser_observe.return_value = mock_snapshot

    result = hybrid_observe(mock_page, mock_registry)

    mock_capture_screenshot.assert_called_once()
    mock_observe.browser_observe.assert_called_once()
    assert result == mock_snapshot


@patch("browser_agent.tools.hybrid_observe.capture_screenshot")
@patch("browser_agent.tools.hybrid_observe.observe")
def test_hybrid_observe_passes_screenshot_path(
    mock_observe: MagicMock,
    mock_capture_screenshot: MagicMock,
    mock_page: MagicMock,
    mock_registry: MagicMock,
) -> None:
    """Test hybrid_observe passes screenshot path to browser_observe."""
    screenshot_path = Path("/tmp/screenshot-123.png")
    mock_capture_screenshot.return_value = screenshot_path
    mock_snapshot = MagicMock(spec=PageSnapshot)
    mock_observe.browser_observe.return_value = mock_snapshot

    hybrid_observe(mock_page, mock_registry)

    mock_observe.browser_observe.assert_called_once()
    call_kwargs = mock_observe.browser_observe.call_args.kwargs
    assert call_kwargs["screenshot_path"] == screenshot_path


@patch("browser_agent.tools.hybrid_observe.capture_screenshot")
@patch("browser_agent.tools.hybrid_observe.observe")
def test_hybrid_observe_passes_max_elements(
    mock_observe: MagicMock,
    mock_capture_screenshot: MagicMock,
    mock_page: MagicMock,
    mock_registry: MagicMock,
) -> None:
    """Test hybrid_observe passes max_elements parameter."""
    mock_capture_screenshot.return_value = Path("/tmp/screenshot.png")
    mock_snapshot = MagicMock(spec=PageSnapshot)
    mock_observe.browser_observe.return_value = mock_snapshot

    hybrid_observe(mock_page, mock_registry, max_elements=40)

    mock_observe.browser_observe.assert_called_once()
    call_kwargs = mock_observe.browser_observe.call_args.kwargs
    assert call_kwargs["max_elements"] == 40


@patch("browser_agent.tools.hybrid_observe.capture_screenshot")
@patch("browser_agent.tools.hybrid_observe.observe")
def test_hybrid_observe_passes_max_text_length(
    mock_observe: MagicMock,
    mock_capture_screenshot: MagicMock,
    mock_page: MagicMock,
    mock_registry: MagicMock,
) -> None:
    """Test hybrid_observe passes max_text_length parameter."""
    mock_capture_screenshot.return_value = Path("/tmp/screenshot.png")
    mock_snapshot = MagicMock(spec=PageSnapshot)
    mock_observe.browser_observe.return_value = mock_snapshot

    hybrid_observe(mock_page, mock_registry, max_text_length=2000)

    mock_observe.browser_observe.assert_called_once()
    call_kwargs = mock_observe.browser_observe.call_args.kwargs
    assert call_kwargs["max_text_length"] == 2000


@patch("browser_agent.tools.hybrid_observe.call_llm")
@patch("builtins.open", new_callable=MagicMock)
def test_invoke_vision_model_default_model(
    mock_open: MagicMock,
    mock_call_llm: MagicMock,
    tmp_path: Path,
) -> None:
    """Test invoke_vision_model uses default GPT-4o model when none specified."""
    screenshot_path = tmp_path / "test.png"
    screenshot_path.write_bytes(b"fake png data")

    mock_file = MagicMock()
    mock_file.read.return_value = b"fake png data"
    mock_open.return_value.__enter__.return_value = mock_file

    mock_call_llm.return_value = "Vision analysis result"

    result = invoke_vision_model(screenshot_path)

    assert mock_call_llm.call_count == 1
    call_args = mock_call_llm.call_args
    assert call_args[1]["model"] == "openai/gpt-4o-2024-08-06"
    assert result == "Vision analysis result"


@patch("browser_agent.tools.hybrid_observe.call_llm")
@patch("builtins.open", new_callable=MagicMock)
def test_invoke_vision_model_custom_model(
    mock_open: MagicMock,
    mock_call_llm: MagicMock,
    tmp_path: Path,
) -> None:
    """Test invoke_vision_model uses custom model when specified."""
    screenshot_path = tmp_path / "test.png"
    screenshot_path.write_bytes(b"fake png data")

    mock_file = MagicMock()
    mock_file.read.return_value = b"fake png data"
    mock_open.return_value.__enter__.return_value = mock_file

    mock_call_llm.return_value = "Custom vision result"

    result = invoke_vision_model(screenshot_path, model="custom/vision-model")

    call_args = mock_call_llm.call_args
    assert call_args[1]["model"] == "custom/vision-model"
    assert result == "Custom vision result"


@patch("browser_agent.tools.hybrid_observe.call_llm")
@patch("builtins.open", new_callable=MagicMock)
def test_invoke_vision_model_custom_prompt(
    mock_open: MagicMock,
    mock_call_llm: MagicMock,
    tmp_path: Path,
) -> None:
    """Test invoke_vision_model uses custom prompt when specified."""
    screenshot_path = tmp_path / "test.png"
    screenshot_path.write_bytes(b"fake png data")

    mock_file = MagicMock()
    mock_file.read.return_value = b"fake png data"
    mock_open.return_value.__enter__.return_value = mock_file

    mock_call_llm.return_value = "Buttons and links detected"

    custom_prompt = "Find all buttons on this page"
    result = invoke_vision_model(screenshot_path, prompt=custom_prompt)

    call_args = mock_call_llm.call_args
    messages = call_args[0][0]
    assert messages[0]["content"][0]["text"] == custom_prompt
    assert result == "Buttons and links detected"


@patch("browser_agent.tools.hybrid_observe.call_llm")
@patch("builtins.open", new_callable=MagicMock)
def test_invoke_vision_model_messages_format(
    mock_open: MagicMock,
    mock_call_llm: MagicMock,
    tmp_path: Path,
) -> None:
    """Test invoke_vision_model creates correct message format with image_url."""
    screenshot_path = tmp_path / "test.png"
    screenshot_path.write_bytes(b"fake png data")

    mock_file = MagicMock()
    mock_file.read.return_value = b"fake png data"
    mock_open.return_value.__enter__.return_value = mock_file

    mock_call_llm.return_value = "Analysis complete"

    invoke_vision_model(screenshot_path)

    call_args = mock_call_llm.call_args
    messages = call_args[0][0]

    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert len(messages[0]["content"]) == 2

    # Check text content
    text_content = messages[0]["content"][0]
    assert text_content["type"] == "text"

    # Check image_url content
    image_content = messages[0]["content"][1]
    assert image_content["type"] == "image_url"
    assert "data:image/png;base64," in image_content["image_url"]["url"]


@patch("browser_agent.tools.hybrid_observe.call_llm")
@patch("builtins.open", new_callable=MagicMock)
def test_invoke_vision_model_reads_screenshot_file(
    mock_open: MagicMock,
    mock_call_llm: MagicMock,
    tmp_path: Path,
) -> None:
    """Test invoke_vision_model reads and encodes the screenshot file."""
    screenshot_path = tmp_path / "test.png"
    test_data = b"test screenshot data"
    screenshot_path.write_bytes(test_data)

    mock_file = MagicMock()
    mock_file.read.return_value = test_data
    mock_open.return_value.__enter__.return_value = mock_file

    mock_call_llm.return_value = "Result"

    invoke_vision_model(screenshot_path)

    mock_open.assert_called_once_with(screenshot_path, "rb")

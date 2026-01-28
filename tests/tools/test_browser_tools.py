"""Tests for browser tools module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agents.tool import ToolContext
from agents.usage import Usage
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from browser_agent.core.registry import ElementRegistry, StaleElementError
from browser_agent.models.element import InteractiveElement
from browser_agent.tools.browser_tools import create_browser_tools


@pytest.fixture
def mock_page() -> MagicMock:
    """Create a mock Playwright Page."""
    page = AsyncMock()
    page.url = "https://example.com"
    page.title = AsyncMock(return_value="Example Domain")
    page.inner_text = AsyncMock(return_value="Hello world")
    page.keyboard = AsyncMock()
    page.mouse = AsyncMock()
    page.locator = MagicMock()
    page.locator.return_value.aria_snapshot = AsyncMock(return_value='- button "Submit"')
    return page


@pytest.fixture
def registry_with_elements() -> ElementRegistry:
    """Create a registry pre-loaded with test elements."""
    registry = ElementRegistry()
    elements = [
        InteractiveElement(ref="elem-0", role="button", name="Submit"),
        InteractiveElement(ref="elem-1", role="link", name="Home"),
        InteractiveElement(ref="elem-2", role="button", name="Delete Account"),
        InteractiveElement(ref="elem-3", role="textbox", name="search"),
    ]
    registry.register_elements(elements)
    return registry


def _get_tool(tools: list, name: str):
    """Get a tool by name from the tools list."""
    for tool in tools:
        if tool.name == name:
            return tool
    raise ValueError(f"Tool {name} not found in {[t.name for t in tools]}")


def _make_ctx() -> ToolContext:
    """Create a minimal ToolContext for testing."""
    return ToolContext(context=None, usage=Usage(), tool_name="test", tool_call_id="test-1", tool_arguments="{}")


class TestBrowserClickSafety:
    def test_destructive_action_blocked(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements, auto_approve=False)
        click_tool = _get_tool(tools, "browser_click")
        ctx = _make_ctx()

        with patch("browser_agent.tools.browser_tools.is_destructive_action", return_value=True), \
             patch("browser_agent.tools.browser_tools.ask_user_confirmation", new_callable=AsyncMock, return_value=False):
            result = asyncio.get_event_loop().run_until_complete(
                click_tool.on_invoke_tool(ctx, '{"element_id": "elem-0"}')
            )
            assert "blocked" in result.lower()

    def test_destructive_action_confirmed(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements, auto_approve=False)
        click_tool = _get_tool(tools, "browser_click")
        ctx = _make_ctx()

        mock_locator = AsyncMock()
        with patch("browser_agent.tools.browser_tools.is_destructive_action", return_value=True), \
             patch("browser_agent.tools.browser_tools.ask_user_confirmation", new_callable=AsyncMock, return_value=True), \
             patch.object(registry_with_elements, "get_locator", return_value=mock_locator):
            result = asyncio.get_event_loop().run_until_complete(
                click_tool.on_invoke_tool(ctx, '{"element_id": "elem-0"}')
            )
            assert "Clicked" in result
            mock_locator.click.assert_awaited_once()

    def test_stale_element_error(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements)
        click_tool = _get_tool(tools, "browser_click")
        ctx = _make_ctx()

        with patch.object(
            registry_with_elements, "get_element",
            side_effect=StaleElementError("elem-0", 0, 1),
        ):
            result = asyncio.get_event_loop().run_until_complete(
                click_tool.on_invoke_tool(ctx, '{"element_id": "elem-0"}')
            )
            assert "browser_observe()" in result
            assert "stale" in result.lower()

    def test_timeout_error(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements)
        click_tool = _get_tool(tools, "browser_click")
        ctx = _make_ctx()

        mock_locator = AsyncMock()
        mock_locator.click = AsyncMock(side_effect=PlaywrightTimeoutError("timeout"))
        # Use elem-1 (link Home) which is not destructive, so no safety prompt
        with patch.object(registry_with_elements, "get_locator", return_value=mock_locator):
            result = asyncio.get_event_loop().run_until_complete(
                click_tool.on_invoke_tool(ctx, '{"element_id": "elem-1"}')
            )
            assert "Timeout" in result


class TestBrowserTypeSafety:
    def test_destructive_check(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements, auto_approve=False)
        type_tool = _get_tool(tools, "browser_type")
        ctx = _make_ctx()

        with patch("browser_agent.tools.browser_tools.is_destructive_action", return_value=True), \
             patch("browser_agent.tools.browser_tools.ask_user_confirmation", new_callable=AsyncMock, return_value=False):
            result = asyncio.get_event_loop().run_until_complete(
                type_tool.on_invoke_tool(ctx, '{"element_id": "elem-0", "text": "hello"}')
            )
            assert "blocked" in result.lower()


class TestBrowserPressSafety:
    def test_enter_triggers_safety_check(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements, auto_approve=False)
        press_tool = _get_tool(tools, "browser_press")
        ctx = _make_ctx()

        # Page title contains a destructive keyword
        mock_page.title = AsyncMock(return_value="submit form page")
        with patch("browser_agent.tools.browser_tools.is_destructive_action", return_value=True), \
             patch("browser_agent.tools.browser_tools.ask_user_confirmation", new_callable=AsyncMock, return_value=False):
            result = asyncio.get_event_loop().run_until_complete(
                press_tool.on_invoke_tool(ctx, '{"key": "Enter"}')
            )
            assert "blocked" in result.lower()

    def test_normal_key_no_safety(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements)
        press_tool = _get_tool(tools, "browser_press")
        ctx = _make_ctx()

        result = asyncio.get_event_loop().run_until_complete(
            press_tool.on_invoke_tool(ctx, '{"key": "Tab"}')
        )
        assert "Pressed key: Tab" in result
        mock_page.keyboard.press.assert_awaited_once_with("Tab")


class TestBrowserNavigate:
    def test_increments_version(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements)
        navigate_tool = _get_tool(tools, "browser_navigate")
        ctx = _make_ctx()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)

        initial_version = registry_with_elements.current_version
        asyncio.get_event_loop().run_until_complete(
            navigate_tool.on_invoke_tool(ctx, '{"url": "https://example.com"}')
        )
        assert registry_with_elements.current_version == initial_version + 1


class TestBrowserObserve:
    def test_formats_elements(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        observe_tool = _get_tool(tools, "browser_observe")
        ctx = _make_ctx()

        # Mock ARIA snapshot with known elements
        mock_page.locator.return_value.aria_snapshot = AsyncMock(
            return_value='- button "Submit"\n- link "Home"'
        )

        result = asyncio.get_event_loop().run_until_complete(
            observe_tool.on_invoke_tool(ctx, "{}")
        )
        assert "Page:" in result
        assert "URL:" in result
        assert "Interactive Elements:" in result

    def test_text_extraction_failure(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        observe_tool = _get_tool(tools, "browser_observe")
        ctx = _make_ctx()

        mock_page.locator.return_value.aria_snapshot = AsyncMock(return_value='- button "Ok"')
        mock_page.inner_text = AsyncMock(side_effect=Exception("text extraction failed"))

        result = asyncio.get_event_loop().run_until_complete(
            observe_tool.on_invoke_tool(ctx, "{}")
        )
        # Should still return a valid observation (text is empty on failure)
        assert "Page:" in result
        assert "Interactive Elements:" in result


class TestBrowserWait:
    def test_clamping_below_minimum(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        wait_tool = _get_tool(tools, "browser_wait")
        ctx = _make_ctx()

        with patch("browser_agent.tools.browser_tools.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = asyncio.get_event_loop().run_until_complete(
                wait_tool.on_invoke_tool(ctx, '{"seconds": 0}')
            )
            assert "Waited 1 seconds" in result
            mock_sleep.assert_awaited_once_with(1)

    def test_clamping_above_maximum(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        wait_tool = _get_tool(tools, "browser_wait")
        ctx = _make_ctx()

        with patch("browser_agent.tools.browser_tools.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = asyncio.get_event_loop().run_until_complete(
                wait_tool.on_invoke_tool(ctx, '{"seconds": 999}')
            )
            assert "Waited 10 seconds" in result
            mock_sleep.assert_awaited_once_with(10)


class TestBrowserExtract:
    def test_extract_title(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        extract_tool = _get_tool(tools, "browser_extract")
        ctx = _make_ctx()

        mock_page.title = AsyncMock(return_value="Example Domain")

        result = asyncio.get_event_loop().run_until_complete(
            extract_tool.on_invoke_tool(ctx, '{"target": "title"}')
        )
        assert "Example Domain" in result

    def test_extract_url(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        extract_tool = _get_tool(tools, "browser_extract")
        ctx = _make_ctx()

        result = asyncio.get_event_loop().run_until_complete(
            extract_tool.on_invoke_tool(ctx, '{"target": "url"}')
        )
        assert "https://example.com" in result

    def test_extract_text(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        extract_tool = _get_tool(tools, "browser_extract")
        ctx = _make_ctx()

        mock_page.inner_text = AsyncMock(return_value="Some page content")

        result = asyncio.get_event_loop().run_until_complete(
            extract_tool.on_invoke_tool(ctx, '{"target": "text"}')
        )
        assert "Some page content" in result

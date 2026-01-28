"""Tests for browser tools module."""

from typing import Any
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
    page.get_by_role = MagicMock()
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


def _get_tool(tools: list, name: str) -> Any:
    """Get a tool by name from the tools list."""
    for tool in tools:
        if tool.name == name:
            return tool
    raise ValueError(f"Tool {name} not found in {[t.name for t in tools]}")


def _make_ctx() -> ToolContext:
    """Create a minimal ToolContext for testing."""
    return ToolContext(context=None, usage=Usage(), tool_name="test", tool_call_id="test-1", tool_arguments="{}")


class TestBrowserClickSafety:
    @pytest.mark.asyncio
    async def test_destructive_action_blocked(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements, auto_approve=False)
        click_tool = _get_tool(tools, "browser_click")
        ctx = _make_ctx()

        with patch("browser_agent.tools.browser_tools.is_destructive_action", return_value=True), \
             patch("browser_agent.tools.browser_tools.ask_user_confirmation", new_callable=AsyncMock, return_value=False):
            result = await click_tool.on_invoke_tool(ctx, '{"element_id": "elem-0"}')
            assert "blocked" in result.lower()

    @pytest.mark.asyncio
    async def test_destructive_action_confirmed(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements, auto_approve=False)
        click_tool = _get_tool(tools, "browser_click")
        ctx = _make_ctx()

        mock_locator = AsyncMock()
        with patch("browser_agent.tools.browser_tools.is_destructive_action", return_value=True), \
             patch("browser_agent.tools.browser_tools.ask_user_confirmation", new_callable=AsyncMock, return_value=True), \
             patch.object(registry_with_elements, "get_locator", return_value=mock_locator):
            result = await click_tool.on_invoke_tool(ctx, '{"element_id": "elem-0"}')
            assert "Clicked" in result
            mock_locator.click.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stale_element_error(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements)
        click_tool = _get_tool(tools, "browser_click")
        ctx = _make_ctx()

        with patch.object(
            registry_with_elements, "get_element",
            side_effect=StaleElementError("elem-0", 0, 1),
        ):
            result = await click_tool.on_invoke_tool(ctx, '{"element_id": "elem-0"}')
            assert "browser_observe()" in result
            assert "stale" in result.lower()

    @pytest.mark.asyncio
    async def test_timeout_error(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements)
        click_tool = _get_tool(tools, "browser_click")
        ctx = _make_ctx()

        mock_locator = AsyncMock()
        mock_locator.click = AsyncMock(side_effect=PlaywrightTimeoutError("timeout"))
        # Use elem-1 (link Home) which is not destructive, so no safety prompt
        with patch.object(registry_with_elements, "get_locator", return_value=mock_locator):
            result = await click_tool.on_invoke_tool(ctx, '{"element_id": "elem-1"}')
            assert "Timeout" in result

    @pytest.mark.asyncio
    async def test_click_key_error(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        """TEST-5: KeyError for unknown element_id."""
        tools = create_browser_tools(mock_page, registry_with_elements)
        click_tool = _get_tool(tools, "browser_click")
        ctx = _make_ctx()

        result = await click_tool.on_invoke_tool(ctx, '{"element_id": "elem-999"}')
        assert "Error" in result
        assert "elem-999" in result


class TestBrowserTypeSafety:
    @pytest.mark.asyncio
    async def test_destructive_check(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements, auto_approve=False)
        type_tool = _get_tool(tools, "browser_type")
        ctx = _make_ctx()

        with patch("browser_agent.tools.browser_tools.is_destructive_action", return_value=True), \
             patch("browser_agent.tools.browser_tools.ask_user_confirmation", new_callable=AsyncMock, return_value=False):
            result = await type_tool.on_invoke_tool(ctx, '{"element_id": "elem-0", "text": "hello"}')
            assert "blocked" in result.lower()

    @pytest.mark.asyncio
    async def test_type_happy_path(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        """TEST-3: Happy path fill."""
        tools = create_browser_tools(mock_page, registry_with_elements)
        type_tool = _get_tool(tools, "browser_type")
        ctx = _make_ctx()

        mock_locator = AsyncMock()
        with patch.object(registry_with_elements, "get_locator", return_value=mock_locator):
            result = await type_tool.on_invoke_tool(ctx, '{"element_id": "elem-3", "text": "hello world"}')
            assert "Typed" in result
            assert "hello world" in result
            mock_locator.fill.assert_awaited_once_with("hello world", timeout=30000)

    @pytest.mark.asyncio
    async def test_type_stale_element(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        """TEST-3: Stale element error."""
        tools = create_browser_tools(mock_page, registry_with_elements)
        type_tool = _get_tool(tools, "browser_type")
        ctx = _make_ctx()

        with patch.object(
            registry_with_elements, "get_element",
            side_effect=StaleElementError("elem-0", 0, 1),
        ):
            result = await type_tool.on_invoke_tool(ctx, '{"element_id": "elem-0", "text": "hello"}')
            assert "stale" in result.lower()

    @pytest.mark.asyncio
    async def test_type_timeout(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        """TEST-3: Timeout error."""
        tools = create_browser_tools(mock_page, registry_with_elements)
        type_tool = _get_tool(tools, "browser_type")
        ctx = _make_ctx()

        mock_locator = AsyncMock()
        mock_locator.fill = AsyncMock(side_effect=PlaywrightTimeoutError("timeout"))
        with patch.object(registry_with_elements, "get_locator", return_value=mock_locator):
            result = await type_tool.on_invoke_tool(ctx, '{"element_id": "elem-3", "text": "hello"}')
            assert "Timeout" in result


class TestBrowserPressSafety:
    @pytest.mark.asyncio
    async def test_enter_triggers_safety_check(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements, auto_approve=False)
        press_tool = _get_tool(tools, "browser_press")
        ctx = _make_ctx()

        # Page title contains a destructive keyword
        mock_page.title = AsyncMock(return_value="submit form page")
        with patch("browser_agent.tools.browser_tools.is_destructive_action", return_value=True), \
             patch("browser_agent.tools.browser_tools.ask_user_confirmation", new_callable=AsyncMock, return_value=False):
            result = await press_tool.on_invoke_tool(ctx, '{"key": "Enter"}')
            assert "blocked" in result.lower()

    @pytest.mark.asyncio
    async def test_normal_key_no_safety(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements)
        press_tool = _get_tool(tools, "browser_press")
        ctx = _make_ctx()

        result = await press_tool.on_invoke_tool(ctx, '{"key": "Tab"}')
        assert "Pressed key: Tab" in result
        mock_page.keyboard.press.assert_awaited_once_with("Tab")


class TestBrowserNavigate:
    @pytest.mark.asyncio
    async def test_increments_version(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        tools = create_browser_tools(mock_page, registry_with_elements)
        navigate_tool = _get_tool(tools, "browser_navigate")
        ctx = _make_ctx()

        mock_response = MagicMock()
        mock_response.status = 200
        mock_page.goto = AsyncMock(return_value=mock_response)

        initial_version = registry_with_elements.current_version
        await navigate_tool.on_invoke_tool(ctx, '{"url": "https://example.com"}')
        assert registry_with_elements.current_version == initial_version + 1

    @pytest.mark.asyncio
    async def test_navigate_timeout(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        """TEST-2: Timeout error on navigation."""
        tools = create_browser_tools(mock_page, registry_with_elements)
        navigate_tool = _get_tool(tools, "browser_navigate")
        ctx = _make_ctx()

        mock_page.goto = AsyncMock(side_effect=PlaywrightTimeoutError("timeout"))
        result = await navigate_tool.on_invoke_tool(ctx, '{"url": "https://slow.example.com"}')
        assert "Timeout" in result

    @pytest.mark.asyncio
    async def test_navigate_http_500(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        """TEST-2: HTTP 500 status."""
        tools = create_browser_tools(mock_page, registry_with_elements)
        navigate_tool = _get_tool(tools, "browser_navigate")
        ctx = _make_ctx()

        mock_response = MagicMock()
        mock_response.status = 500
        mock_page.goto = AsyncMock(return_value=mock_response)

        result = await navigate_tool.on_invoke_tool(ctx, '{"url": "https://broken.example.com"}')
        assert "500" in result

    @pytest.mark.asyncio
    async def test_navigate_null_response(self, mock_page: MagicMock, registry_with_elements: ElementRegistry) -> None:
        """TEST-2: Null response from goto."""
        tools = create_browser_tools(mock_page, registry_with_elements)
        navigate_tool = _get_tool(tools, "browser_navigate")
        ctx = _make_ctx()

        mock_page.goto = AsyncMock(return_value=None)
        result = await navigate_tool.on_invoke_tool(ctx, '{"url": "https://example.com"}')
        assert "Navigated" in result


class TestBrowserObserve:
    @pytest.mark.asyncio
    async def test_formats_elements(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        observe_tool = _get_tool(tools, "browser_observe")
        ctx = _make_ctx()

        # Mock ARIA snapshot with known elements
        mock_page.locator.return_value.aria_snapshot = AsyncMock(
            return_value='- button "Submit"\n- link "Home"'
        )

        result = await observe_tool.on_invoke_tool(ctx, "{}")
        assert "Page:" in result
        assert "URL:" in result
        assert "Interactive Elements:" in result

    @pytest.mark.asyncio
    async def test_text_extraction_failure(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        observe_tool = _get_tool(tools, "browser_observe")
        ctx = _make_ctx()

        mock_page.locator.return_value.aria_snapshot = AsyncMock(return_value='- button "Ok"')
        mock_page.inner_text = AsyncMock(side_effect=Exception("text extraction failed"))

        result = await observe_tool.on_invoke_tool(ctx, "{}")
        # Should still return a valid observation with fallback text
        assert "Page:" in result
        assert "Interactive Elements:" in result
        assert "Text extraction failed" in result


class TestBrowserWait:
    @pytest.mark.asyncio
    async def test_clamping_below_minimum(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        wait_tool = _get_tool(tools, "browser_wait")
        ctx = _make_ctx()

        with patch("browser_agent.tools.browser_tools.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await wait_tool.on_invoke_tool(ctx, '{"seconds": 0}')
            assert "Waited 1 seconds" in result
            mock_sleep.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_clamping_above_maximum(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        wait_tool = _get_tool(tools, "browser_wait")
        ctx = _make_ctx()

        with patch("browser_agent.tools.browser_tools.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await wait_tool.on_invoke_tool(ctx, '{"seconds": 999}')
            assert "Waited 10 seconds" in result
            mock_sleep.assert_awaited_once_with(10)


class TestBrowserScroll:
    @pytest.mark.asyncio
    async def test_scroll_down(self, mock_page: MagicMock) -> None:
        """TEST-4: Scroll down by 500px."""
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        scroll_tool = _get_tool(tools, "browser_scroll")
        ctx = _make_ctx()

        result = await scroll_tool.on_invoke_tool(ctx, '{"direction": "down"}')
        assert "Scrolled down by 500px" in result
        mock_page.mouse.wheel.assert_awaited_once_with(0, 500)

    @pytest.mark.asyncio
    async def test_scroll_up(self, mock_page: MagicMock) -> None:
        """TEST-4: Scroll up by -500px."""
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        scroll_tool = _get_tool(tools, "browser_scroll")
        ctx = _make_ctx()

        result = await scroll_tool.on_invoke_tool(ctx, '{"direction": "up"}')
        assert "Scrolled up by 500px" in result
        mock_page.mouse.wheel.assert_awaited_once_with(0, -500)

    @pytest.mark.asyncio
    async def test_scroll_invalid_direction(self, mock_page: MagicMock) -> None:
        """TEST-4: Invalid direction returns error."""
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        scroll_tool = _get_tool(tools, "browser_scroll")
        ctx = _make_ctx()

        result = await scroll_tool.on_invoke_tool(ctx, '{"direction": "left"}')
        assert "Error" in result
        assert "Invalid" in result


class TestBrowserExtract:
    @pytest.mark.asyncio
    async def test_extract_title(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        extract_tool = _get_tool(tools, "browser_extract")
        ctx = _make_ctx()

        mock_page.title = AsyncMock(return_value="Example Domain")

        result = await extract_tool.on_invoke_tool(ctx, '{"target": "title"}')
        assert "Example Domain" in result

    @pytest.mark.asyncio
    async def test_extract_url(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        extract_tool = _get_tool(tools, "browser_extract")
        ctx = _make_ctx()

        result = await extract_tool.on_invoke_tool(ctx, '{"target": "url"}')
        assert "https://example.com" in result

    @pytest.mark.asyncio
    async def test_extract_text(self, mock_page: MagicMock) -> None:
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        extract_tool = _get_tool(tools, "browser_extract")
        ctx = _make_ctx()

        mock_page.inner_text = AsyncMock(return_value="Some page content")

        result = await extract_tool.on_invoke_tool(ctx, '{"target": "text"}')
        assert "Some page content" in result

    @pytest.mark.asyncio
    async def test_extract_links(self, mock_page: MagicMock) -> None:
        """TEST-6: Extract links using get_by_role."""
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        extract_tool = _get_tool(tools, "browser_extract")
        ctx = _make_ctx()

        mock_link = AsyncMock()
        mock_link.inner_text = AsyncMock(return_value="Example Link")
        mock_link.get_attribute = AsyncMock(return_value="https://example.com/page")
        mock_page.get_by_role.return_value.all = AsyncMock(return_value=[mock_link])

        result = await extract_tool.on_invoke_tool(ctx, '{"target": "links"}')
        assert "Example Link" in result
        assert "https://example.com/page" in result

    @pytest.mark.asyncio
    async def test_extract_inputs(self, mock_page: MagicMock) -> None:
        """TEST-6: Extract form inputs using get_by_role."""
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        extract_tool = _get_tool(tools, "browser_extract")
        ctx = _make_ctx()

        mock_input = AsyncMock()
        mock_input.get_attribute = AsyncMock(side_effect=lambda attr: {
            "type": "text", "name": "username", "placeholder": "Enter username"
        }.get(attr, ""))
        mock_page.get_by_role.return_value.all = AsyncMock(return_value=[mock_input])

        result = await extract_tool.on_invoke_tool(ctx, '{"target": "inputs"}')
        assert "inputs" in result.lower() or "Found" in result

    @pytest.mark.asyncio
    async def test_extract_unknown_target(self, mock_page: MagicMock) -> None:
        """TEST-6: Fallback for unknown target."""
        registry = ElementRegistry()
        tools = create_browser_tools(mock_page, registry)
        extract_tool = _get_tool(tools, "browser_extract")
        ctx = _make_ctx()

        mock_page.inner_text = AsyncMock(return_value="Fallback page content here")

        result = await extract_tool.on_invoke_tool(ctx, '{"target": "something_else"}')
        assert "Fallback page content" in result

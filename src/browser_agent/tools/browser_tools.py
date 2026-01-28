"""Browser tools as @function_tool for the OpenAI Agents SDK.

This module provides a factory function that creates browser action tools
as @function_tool decorated async functions. The factory uses closures so
each tool captures the async Playwright Page and ElementRegistry.
"""

import asyncio
from typing import Any, cast

from agents import function_tool
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from browser_agent.core.logging import ErrorIds, logError, logForDebugging
from browser_agent.core.registry import ElementRegistry, StaleElementError
from browser_agent.tools.observe import _extract_interactive_elements
from browser_agent.tools.safety import ask_user_confirmation, is_destructive_action


def create_browser_tools(page: Page, registry: ElementRegistry, auto_approve: bool = False) -> list[Any]:
    """Create browser tools as @function_tool decorated async functions.

    Each tool is a closure that captures the async Playwright Page and
    ElementRegistry, allowing the SDK agent to call them through the
    ReAct loop without passing page/registry explicitly.

    Args:
        page: The async Playwright Page object.
        registry: The ElementRegistry for managing element references.
        auto_approve: If True, skip user confirmation for destructive actions.

    Returns:
        A list of FunctionTool instances for the SDK agent.
    """

    @function_tool
    async def browser_observe() -> str:
        """Observe the current page state. Returns the page title, URL, a list of interactive elements with IDs, and visible text.

        ALWAYS call this tool first before taking any action on the page.
        Use the element IDs (e.g., 'elem-0') from the observation to interact
        with elements via browser_click, browser_type, etc.
        After any navigation or major page change, call this again to get fresh element references.
        """
        url = page.url
        title = await page.title()

        # Get ARIA snapshot and parse interactive elements
        aria_yaml = await page.locator("body").aria_snapshot()
        elements = _extract_interactive_elements(aria_yaml, max_elements=60)

        # Register elements with the registry (assigns refs, tracks version)
        registry.register_elements(elements)

        # Get visible text excerpt
        try:
            text = await page.inner_text("body", timeout=5000)
            text = " ".join(text.split())
            if len(text) > 3000:
                text = text[:3000] + "..."
        except Exception as e:
            logError(
                ErrorIds.VISIBLE_TEXT_EXTRACTION_FAILED,
                f"Failed to extract visible text: {e}",
                exc_info=True,
            )
            text = ""

        # Format output for the LLM
        lines = [f"Page: {title}", f"URL: {url}", "", "Interactive Elements:"]
        for elem in elements:
            line = f'- {elem.ref}: [{elem.role}] "{elem.name}"'
            if elem.value_preview:
                line += f" (value: {elem.value_preview})"
            lines.append(line)

        if not elements:
            lines.append("  (no interactive elements found)")

        lines.append("")
        lines.append(f"Visible Text (first 3000 chars):\n{text}")

        return "\n".join(lines)

    @function_tool
    async def browser_click(element_id: str) -> str:
        """Click an interactive element on the page.

        Args:
            element_id: The element reference ID from browser_observe (e.g., 'elem-0').
        """
        try:
            element = registry.get_element(element_id)
            # Safety check: confirm before destructive actions
            action_desc = f"{element.role} {element.name}"
            if is_destructive_action(action_desc):
                confirmed = await ask_user_confirmation(action_desc, auto_approve=auto_approve)
                if not confirmed:
                    return "Action blocked by user"
            locator: Any = registry.get_locator(cast(Any, page), element_id)
            await locator.click(timeout=30000)
            logForDebugging(f'Clicked [{element.role}] "{element.name}" ({element_id})')
            return f'Clicked [{element.role}] "{element.name}" ({element_id})'
        except StaleElementError as e:
            logError(ErrorIds.STALE_ELEMENT_REFERENCE, str(e), extra={"element_id": element_id})
            return f"Error: {e}. Call browser_observe() to get fresh element references."
        except KeyError as e:
            logError(ErrorIds.ELEMENT_NOT_FOUND, str(e), extra={"element_id": element_id})
            return f"Error: {e}"
        except PlaywrightTimeoutError:
            logError(ErrorIds.CLICK_TIMEOUT, f"Timeout clicking {element_id}", extra={"element_id": element_id})
            return f"Error: Timeout clicking {element_id}. The element may be hidden or not clickable. Try browser_observe() to refresh."
        except Exception as e:
            logError(ErrorIds.ELEMENT_INTERACTION_FAILED, f"Error clicking {element_id}: {e}", exc_info=True)
            return f"Error clicking {element_id}: {e}"

    @function_tool
    async def browser_type(element_id: str, text: str) -> str:
        """Type text into an input element on the page (replaces existing content).

        Args:
            element_id: The element reference ID from browser_observe (e.g., 'elem-0').
            text: The text to type into the element.
        """
        try:
            element = registry.get_element(element_id)
            # Safety check: confirm before destructive actions
            action_desc = f"{element.role} {element.name}"
            if is_destructive_action(action_desc):
                confirmed = await ask_user_confirmation(action_desc, auto_approve=auto_approve)
                if not confirmed:
                    return "Action blocked by user"
            locator: Any = registry.get_locator(cast(Any, page), element_id)
            await locator.fill(text, timeout=30000)
            logForDebugging(f'Typed into [{element.role}] "{element.name}" ({element_id})')
            return f'Typed "{text}" into [{element.role}] "{element.name}" ({element_id})'
        except StaleElementError as e:
            logError(ErrorIds.STALE_ELEMENT_REFERENCE, str(e), extra={"element_id": element_id})
            return f"Error: {e}. Call browser_observe() to get fresh element references."
        except KeyError as e:
            logError(ErrorIds.ELEMENT_NOT_FOUND, str(e), extra={"element_id": element_id})
            return f"Error: {e}"
        except PlaywrightTimeoutError:
            logError(ErrorIds.TYPE_TIMEOUT, f"Timeout typing into {element_id}", extra={"element_id": element_id})
            return f"Error: Timeout typing into {element_id}. The element may not be editable."
        except Exception as e:
            logError(ErrorIds.ELEMENT_INTERACTION_FAILED, f"Error typing into {element_id}: {e}", exc_info=True)
            return f"Error typing into {element_id}: {e}"

    @function_tool
    async def browser_press(key: str) -> str:
        """Press a keyboard key.

        Args:
            key: The key to press (e.g., 'Enter', 'Tab', 'Escape', 'ArrowDown', 'Backspace', 'Space').
        """
        try:
            # Enter key can trigger form submission — apply safety check
            if key.lower() == "enter":
                title = await page.title()
                action_desc = f"press Enter on {title}"
                if is_destructive_action(action_desc):
                    confirmed = await ask_user_confirmation(action_desc, auto_approve=auto_approve)
                    if not confirmed:
                        return "Action blocked by user"
            await page.keyboard.press(key)
            logForDebugging(f"Pressed key: {key}")
            return f"Pressed key: {key}"
        except Exception as e:
            logError(ErrorIds.ELEMENT_INTERACTION_FAILED, f"Error pressing key {key}: {e}", exc_info=True)
            return f"Error pressing key {key}: {e}"

    @function_tool
    async def browser_scroll(direction: str) -> str:
        """Scroll the page up or down by 500 pixels.

        Args:
            direction: Scroll direction, either 'up' or 'down'.
        """
        try:
            delta = -500 if direction.lower() == "up" else 500
            await page.mouse.wheel(0, delta)
            logForDebugging(f"Scrolled {direction} by 500px")
            return f"Scrolled {direction} by 500px"
        except Exception as e:
            logError(ErrorIds.ELEMENT_INTERACTION_FAILED, f"Error scrolling {direction}: {e}", exc_info=True)
            return f"Error scrolling {direction}: {e}"

    @function_tool
    async def browser_navigate(url: str) -> str:
        """Navigate to a URL. After navigation, call browser_observe() to see the new page state.

        Args:
            url: The full URL to navigate to (e.g., 'https://example.com').
        """
        try:
            response = await page.goto(url, wait_until="load", timeout=30000)
            # Navigation changes the page — old element refs are stale
            registry.increment_version()
            if response is None:
                logForDebugging(f"Navigated to {url}")
                return f"Navigated to {url}"
            status = response.status
            if 200 <= status < 400:
                logForDebugging(f"Navigated to {url} (status: {status})")
                return f"Navigated to {url} (status: {status})"
            else:
                logForDebugging(f"Navigation to {url} returned HTTP {status}", level="warning")
                return f"Navigation to {url} returned HTTP {status}"
        except PlaywrightTimeoutError:
            logError(ErrorIds.NAVIGATION_FAILED, f"Timeout navigating to {url}", extra={"url": url})
            return f"Error: Timeout navigating to {url}. The page may be slow to load."
        except Exception as e:
            logError(ErrorIds.NAVIGATION_FAILED, f"Error navigating to {url}: {e}", exc_info=True)
            return f"Error navigating to {url}: {e}"

    @function_tool
    async def browser_wait(seconds: int) -> str:
        """Wait for a specified number of seconds (max 10). Use when the page needs time to load or update.

        Args:
            seconds: Number of seconds to wait (clamped to 1-10).
        """
        wait_time = min(max(seconds, 1), 10)
        await asyncio.sleep(wait_time)
        return f"Waited {wait_time} seconds"

    @function_tool
    async def browser_extract(target: str) -> str:
        """Extract specific data from the current page.

        Args:
            target: What to extract. Use 'title' for page title, 'url' for page URL, 'text' for page text content, 'links' for all links, or 'inputs' for form inputs.
        """
        try:
            target_lower = target.lower()

            if "title" in target_lower:
                title = await page.title()
                return f"Page title: {title}"

            elif "url" in target_lower or "address" in target_lower:
                return f"Page URL: {page.url}"

            elif "text" in target_lower or "content" in target_lower:
                text = await page.inner_text("body", timeout=5000)
                return f"Page text content (truncated to 4000 chars):\n{text[:4000]}"

            elif "link" in target_lower or "anchor" in target_lower:
                links = await page.locator("a").all()
                link_texts = []
                for link in links[:20]:
                    lt = await link.inner_text()
                    href = await link.get_attribute("href") or ""
                    link_texts.append(f"  {lt} ({href})")
                return f"Found {len(links)} links. First 20:\n" + "\n".join(link_texts)

            elif "input" in target_lower or "form" in target_lower:
                inputs = await page.locator("input, textarea, select").all()
                input_info = []
                for inp in inputs[:20]:
                    inp_type = await inp.get_attribute("type") or "text"
                    inp_name = await inp.get_attribute("name") or ""
                    inp_placeholder = await inp.get_attribute("placeholder") or ""
                    input_info.append(
                        f"  {inp_type}(name={inp_name!r}, placeholder={inp_placeholder!r})"
                    )
                return f"Found {len(inputs)} inputs. First 20:\n" + "\n".join(input_info)

            else:
                text = await page.inner_text("body", timeout=5000)
                return f"Page content (first 2000 chars):\n{text[:2000]}"

        except Exception as e:
            return f"Error extracting '{target}': {e}"

    @function_tool
    async def browser_done(summary: str) -> str:
        """Signal that the current task is complete and provide a summary of what was accomplished.

        Call this when you have finished the assigned task. The summary becomes the final output.

        Args:
            summary: A clear summary of what was accomplished during the task.
        """
        return summary

    @function_tool
    async def ask_user(question: str) -> str:
        """Ask the user a question and wait for their response. Use when you need clarification, login credentials, a choice between options, or any human input.

        This blocks execution until the user responds in the terminal.

        Args:
            question: The question to ask the user.
        """
        from rich.console import Console
        from rich.prompt import Prompt

        console = Console()

        def _prompt() -> str:
            console.print(f"\n[bold yellow]Agent asks:[/bold yellow] {question}")
            return Prompt.ask("[bold green]Your answer[/bold green]")

        answer = await asyncio.to_thread(_prompt)
        return answer

    return [
        browser_observe,
        browser_click,
        browser_type,
        browser_press,
        browser_scroll,
        browser_navigate,
        browser_wait,
        browser_extract,
        browser_done,
        ask_user,
    ]

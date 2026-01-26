"""Extract action tool for browser automation.

This module provides the extract function for extracting data from the page.
"""

from typing import cast

from playwright.sync_api import Page

from browser_agent.models.result import ActionResult, failure_result, success_result


def extract(page: Page, target: str) -> ActionResult:
    """Extract data from the page based on a target description.

    Args:
        page: The Playwright Page object.
        target: Description of what to extract (e.g., "page title", "all links",
                "text content", "form inputs").

    Returns:
        ActionResult with the extracted data in the message field.

    Note:
        This is a generic extraction helper. For complex extraction needs,
        consider using page.evaluate() with custom JavaScript or page.content()
        for full HTML.
    """
    try:
        target_lower = target.lower()

        # Handle common extraction targets
        if "title" in target_lower:
            result = cast(str, page.title)
            return success_result(
                message=f"Page title: {result}",
            )

        elif "url" in target_lower or "address" in target_lower:
            result = cast(str, page.url)
            return success_result(
                message=f"Page URL: {result}",
            )

        elif "text" in target_lower or "content" in target_lower:
            result = cast(str, page.inner_text("body")[:4000])  # Limit to 4K chars
            return success_result(
                message=f"Page text content (truncated): {result}",
            )

        elif "link" in target_lower or "anchor" in target_lower:
            links = page.locator("a").all()
            link_texts = [link.inner_text() for link in links[:20]]  # Limit to 20
            return success_result(
                message=f"Found {len(links)} links. First 20: {link_texts}",
            )

        elif "input" in target_lower or "form" in target_lower:
            inputs = page.locator("input, textarea, select").all()
            input_info = []
            for inp in inputs[:20]:  # Limit to 20
                inp_type = inp.get_attribute("type") or "text"
                inp_name = inp.get_attribute("name") or ""
                inp_placeholder = inp.get_attribute("placeholder") or ""
                input_info.append(f"{inp_type}(name={inp_name!r}, placeholder={inp_placeholder!r})")
            return success_result(
                message=f"Found {len(inputs)} inputs. First 20: {input_info}",
            )

        else:
            # Generic fallback: return page text
            result = cast(str, page.inner_text("body")[:2000])
            return success_result(
                message=f"Page content (first 2000 chars): {result}",
            )

    except Exception as e:
        return failure_result(
            message=f"Failed to extract {target!r} from page",
            error=str(e),
        )

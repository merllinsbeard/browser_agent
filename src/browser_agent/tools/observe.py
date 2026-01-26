"""Page observation tool for browser automation.

This module provides the browser_observe function for observing
page state without full DOM dumps.
"""

from pathlib import Path
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]
from playwright.sync_api import Page

from browser_agent.core.registry import ElementRegistry
from browser_agent.models.element import BoundingBox, InteractiveElement
from browser_agent.models.snapshot import PageSnapshot


# Priority roles to capture (higher = more important)
_ROLE_PRIORITY: dict[str, int] = {
    "button": 10,
    "link": 9,
    "textbox": 8,
    "searchbox": 8,
    "textarea": 8,
    "combobox": 8,
    "listbox": 7,
    "checkbox": 7,
    "radio": 7,
    "switch": 7,
    "slider": 6,
    "spinbutton": 6,
    "menu": 5,
    "menuitem": 5,
    "tab": 5,
    "grid": 4,
    "table": 4,
    "list": 3,
    "listitem": 3,
    "dialog": 2,
    "alert": 2,
    "banner": 1,
    "navigation": 1,
    "main": 1,
}


def browser_observe(
    page: Page,
    registry: ElementRegistry,
    max_elements: int = 60,
    max_text_length: int = 3000,
    screenshot_path: Path | None = None,
) -> PageSnapshot:
    """Observe the current page state.

    Uses Playwright's aria_snapshot() for compact, semantic page representation.
    Extracts interactive elements, visible text, and metadata.

    Args:
        page: The Playwright Page object.
        registry: The ElementRegistry for registering element references.
        max_elements: Maximum number of interactive elements to capture.
        max_text_length: Maximum length of visible text excerpt.
        screenshot_path: Optional path to a screenshot file.

    Returns:
        A PageSnapshot containing the observed page state.
    """
    # Get basic page info
    url = page.url
    title = page.title()

    # Get the ARIA snapshot YAML
    aria_yaml = page.locator("body").aria_snapshot()

    # Parse YAML and extract interactive elements
    elements = _extract_interactive_elements(aria_yaml, max_elements)

    # Register elements with the registry
    selectors = [f"[role={e.role}]" for e in elements]  # Simplified selectors
    result = registry.register_elements(elements, selectors)
    current_version = result.snapshot_version

    # Get visible text excerpt (truncated)
    visible_text = _get_visible_text(page, max_text_length)

    # Collect notes about the page state
    notes: list[str] = []
    if screenshot_path:
        notes.append(f"Screenshot saved to: {screenshot_path}")

    return PageSnapshot(
        url=url,
        title=title,
        interactive_elements=elements,
        visible_text_excerpt=visible_text,
        screenshot_path=screenshot_path,
        notes=notes,
        version=current_version,
    )


def _extract_interactive_elements(aria_yaml: str, max_elements: int) -> list[InteractiveElement]:
    """Extract interactive elements from ARIA snapshot YAML.

    Args:
        aria_yaml: The ARIA snapshot YAML string.
        max_elements: Maximum number of elements to extract.

    Returns:
        List of InteractiveElement objects.
    """
    try:
        parsed = yaml.safe_load(aria_yaml)
    except yaml.YAMLError:
        # If YAML parsing fails, return empty list
        return []

    elements: list[dict] = []
    _traverse_aria_tree(parsed, elements)

    # Sort by priority and limit to max_elements
    elements.sort(key=lambda e: _ROLE_PRIORITY.get(e.get("role", ""), 0), reverse=True)
    elements = elements[:max_elements]

    # Convert to InteractiveElement objects
    result = []
    for i, elem in enumerate(elements):
        role = elem.get("role", "unknown")
        name = elem.get("name", "")
        attributes = elem.get("attributes", {})

        result.append(
            InteractiveElement(
                ref=f"elem-{i}",
                role=role,
                name=name,
                aria_label=attributes.get("aria-label"),
                placeholder=attributes.get("placeholder"),
                value_preview=elem.get("value", "")[:100],
                bbox=None,  # BoundingBox not available from ARIA snapshot
            )
        )

    return result


def _traverse_aria_tree(node: Any, elements: list[dict]) -> None:
    """Traverse the ARIA tree and collect interactive elements.

    Args:
        node: Current node in the tree (can be dict, list, or string).
        elements: Accumulator list for interactive elements.
    """
    if isinstance(node, dict):
        # Check if this is an interactive element
        role = node.get("role", "")
        if role in _ROLE_PRIORITY:
            elements.append(node)

        # Recurse into children
        for key, value in node.items():
            if key not in ("role", "name", "attributes"):
                _traverse_aria_tree(value, elements)

    elif isinstance(node, list):
        for item in node:
            _traverse_aria_tree(item, elements)


def _get_visible_text(page: Page, max_length: int) -> str:
    """Get visible text from the page, truncated to max_length.

    Args:
        page: The Playwright Page object.
        max_length: Maximum length of text to return.

    Returns:
        Visible text excerpt.
    """
    try:
        # Get text from body
        text = page.inner_text("body", timeout=5000)
        # Clean up whitespace
        text = " ".join(text.split())
        # Truncate
        if len(text) > max_length:
            text = text[:max_length] + "..."
        return text
    except Exception:
        return ""

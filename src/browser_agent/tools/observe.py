"""Page observation tool for browser automation.

This module provides the browser_observe function for observing
page state without full DOM dumps.
"""

import re
from typing import Any

import yaml  # type: ignore[import-untyped]
from playwright.sync_api import Page

from browser_agent.core.registry import ElementRegistry
from browser_agent.models.element import BoundingBox, InteractiveElement
from browser_agent.models.snapshot import PageSnapshot


# Regex to parse ARIA node strings like: heading "Example Domain" [level=1]
# Group 1: role (e.g., "heading"), Group 2: name (e.g., "Example Domain"), Group 3: attributes (e.g., "level=1")
_ARIA_NODE_PATTERN = re.compile(r'^(\w+)(?:\s+"(.*)")?(?:\s+\[(.+)\])?$')

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
    screenshot_path: str | None = None,
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

    # Register elements with the registry (groups by role+name for nth disambiguation)
    result = registry.register_elements(elements)
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

    elements: list[dict[str, Any]] = []
    _traverse_aria_tree(parsed, elements)

    # Sort by priority and limit to max_elements
    elements.sort(key=lambda e: _ROLE_PRIORITY.get(e.get("role", ""), 0), reverse=True)
    elements = elements[:max_elements]

    # Convert to InteractiveElement objects
    result = []
    for i, elem in enumerate(elements):
        role = elem.get("role", "unknown")
        name = elem.get("name", "")
        attributes: dict[str, str] = elem.get("attributes", {})
        value = attributes.get("value", "")

        result.append(
            InteractiveElement(
                ref=f"elem-{i}",
                role=role,
                name=name,
                aria_label=attributes.get("aria-label"),
                placeholder=attributes.get("placeholder"),
                value_preview=value[:100] if value else None,
                bbox=None,  # BoundingBox not available from ARIA snapshot
            )
        )

    return result


def _traverse_aria_tree(node: Any, elements: list[dict[str, Any]]) -> None:
    """Traverse the ARIA tree and collect interactive elements.

    Playwright's aria_snapshot() returns YAML where:
    - String items encode role+name: 'link "More information..."'
    - Dict keys encode role+name: {'heading "Example Domain" [level=1]': children}
    - Values can be strings (text content), lists (children), or None

    Args:
        node: Current node in the tree (can be dict, list, or string).
        elements: Accumulator list for interactive element dicts.
    """
    if isinstance(node, list):
        for item in node:
            _traverse_aria_tree(item, elements)

    elif isinstance(node, dict):
        for key, value in node.items():
            # Skip metadata keys like /url
            if isinstance(key, str) and key.startswith("/"):
                continue
            _process_aria_node(str(key), value, elements)

    elif isinstance(node, str):
        # String item in a list: 'heading "Example Domain" [level=1]'
        _process_aria_node(node, None, elements)


def _process_aria_node(
    key: str, value: Any, elements: list[dict[str, Any]]
) -> None:
    """Process a single ARIA node (string or dict key).

    Parses the key string to extract role, name, and attributes using
    the _ARIA_NODE_PATTERN regex.

    Args:
        key: The string to parse (role + optional name + optional attributes).
        value: The value associated with this key (children, text, or None).
        elements: Accumulator list for interactive element dicts.
    """
    match = _ARIA_NODE_PATTERN.match(key)
    if not match:
        return

    role = match.group(1)
    name = match.group(2) or ""
    attrs_str = match.group(3)

    # Skip text role (not interactive)
    if role == "text":
        return

    # Parse attributes like "level=1, checked=true" into dict
    attributes: dict[str, str] = {}
    if attrs_str:
        for attr in attrs_str.split(","):
            attr = attr.strip()
            if "=" in attr:
                attr_key, _, attr_value = attr.partition("=")
                attributes[attr_key.strip()] = attr_value.strip()

    # If role is in priority list, add to elements
    if role in _ROLE_PRIORITY:
        elements.append({
            "role": role,
            "name": name,
            "attributes": attributes,
        })

    # Recurse into children
    if isinstance(value, list):
        _traverse_aria_tree(value, elements)
    elif isinstance(value, dict):
        _traverse_aria_tree(value, elements)


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

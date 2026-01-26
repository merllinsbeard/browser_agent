"""Hybrid observation tool with screenshot fallback.

This module provides page observation with automatic screenshot capture
for cases where the accessibility tree is insufficient.
"""

from pathlib import Path

from playwright.sync_api import Page

from browser_agent.core.registry import ElementRegistry
from browser_agent.models.snapshot import PageSnapshot
from browser_agent.tools.screenshot import capture_screenshot
from browser_agent.tools import observe


def hybrid_observe(
    page: Page,
    registry: ElementRegistry,
    screenshot_dir: Path | None = None,
    max_elements: int = 60,
    max_text_length: int = 3000,
) -> PageSnapshot:
    """Observe page state with automatic screenshot capture.

    Combines ARIA-based observation with screenshot capture for
    fallback visual analysis when the accessibility tree is insufficient.

    Args:
        page: The Playwright Page object.
        registry: The ElementRegistry for tracking element references.
        screenshot_dir: Directory to save screenshots. If None, uses default.
        max_elements: Maximum number of interactive elements to include.
        max_text_length: Maximum length of visible text excerpt.

    Returns:
        PageSnapshot with screenshot_path included for visual analysis.
    """
    # Capture screenshot first (before any page modifications)
    screenshot_path = capture_screenshot(
        page,
        output_path=screenshot_dir,
        full_page=False,
    )

    # Get the ARIA-based snapshot
    snapshot = observe.browser_observe(
        page,
        registry,
        max_elements=max_elements,
        max_text_length=max_text_length,
        screenshot_path=screenshot_path,
    )

    return snapshot


def needs_vision_fallback(snapshot: PageSnapshot, threshold: int = 10) -> bool:
    """Check if vision model analysis is needed based on element count.

    Args:
        snapshot: The PageSnapshot to analyze.
        threshold: Element count below which vision is recommended (default 10).

    Returns:
        True if vision model analysis is recommended.
    """
    return len(snapshot.interactive_elements) < threshold

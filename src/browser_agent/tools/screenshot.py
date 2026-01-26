"""Screenshot capture tool for browser automation.

This module provides the capture_screenshot function for capturing
page screenshots for fallback analysis.
"""

from pathlib import Path

from playwright.sync_api import Page


def capture_screenshot(
    page: Page,
    output_path: Path | str | None = None,
    full_page: bool = False,
) -> Path:
    """Capture a screenshot of the current page.

    Args:
        page: The Playwright Page object.
        output_path: Path where screenshot should be saved.
                     If None, generates a timestamped filename in current directory.
        full_page: If True, captures the full scrollable page.
                  If False, captures only the viewport.

    Returns:
        Path to the saved screenshot.

    Raises:
        Exception: If screenshot capture fails.
    """
    if output_path is None:
        import time

        timestamp = int(time.time() * 1000)
        output_path = Path(f"screenshot-{timestamp}.png")
    else:
        output_path = Path(output_path)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Capture screenshot
    page.screenshot(path=str(output_path), full_page=full_page)

    return output_path

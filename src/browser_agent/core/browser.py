"""Browser context management for persistent sessions.

This module provides functions to launch and manage Playwright browser contexts
with persistent storage for session data (cookies, localStorage, etc.).
"""

from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Playwright


def launch_persistent_context(
    playwright: Playwright,
    user_data_dir: str | Path,
    headless: bool = False,
) -> BrowserContext:
    """Launch a browser with persistent storage for session data.

    This function creates a browser context that persists cookies, localStorage,
    and other session data to disk. The context remains alive until closed.

    Args:
        playwright: The Playwright instance (from sync_playwright()).
        user_data_dir: Path to directory where session data will be stored.
                      Directory will be created if it doesn't exist.
        headless: If False (default), launches in visible (headful) mode.
                 If True, launches in headless mode without UI.

    Returns:
        A BrowserContext instance. The browser can be accessed via
        context.browser and will be closed when the context is closed.

    Example:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            context = launch_persistent_context(p, "./session", headless=False)
            page = context.new_page()
            page.goto("https://example.com")
            # ... perform actions ...
            context.close()  # Also closes the browser

    Note:
        - Only ONE browser instance can use a given user_data_dir at a time.
        - Using Chrome/Edge's main user profile is NOT supported by Chrome policies.
          Use a dedicated directory (e.g., empty folder) instead.
        - The browser is automatically closed when the context is closed.
    """
    context = playwright.chromium.launch_persistent_context(
        user_data_dir=str(user_data_dir),
        headless=headless,
    )
    return context

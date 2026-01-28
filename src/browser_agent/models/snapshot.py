"""Page snapshot models for browser observation.

This module defines the PageSnapshot model which represents
the current state of a web page for agent observation.
"""

from pydantic import BaseModel, ConfigDict

from browser_agent.models.element import InteractiveElement


class PageSnapshot(BaseModel):
    """A snapshot of the current page state.

    This represents a compact view of the page for the agent to use
    when deciding what action to take next. It includes the URL, title,
    interactive elements, visible text excerpt, and optional screenshot.

    Attributes:
        url: The current page URL.
        title: The page title.
        interactive_elements: List of interactive elements on the page.
        visible_text_excerpt: Truncated visible text from the page (2-4K chars).
        screenshot_path: Optional path to a screenshot of the page.
        notes: Additional observations (popups, navigation in progress, etc.).
        version: Snapshot version for element validation (increments on new observation).
    """

    model_config = ConfigDict(frozen=True)

    url: str
    title: str
    interactive_elements: list[InteractiveElement] = []
    visible_text_excerpt: str = ""
    screenshot_path: str | None = None
    notes: list[str] = []
    version: int = 0

    def with_version(self, new_version: int) -> "PageSnapshot":
        """Return a new snapshot with an incremented version."""
        return PageSnapshot(
            url=self.url,
            title=self.title,
            interactive_elements=self.interactive_elements,
            visible_text_excerpt=self.visible_text_excerpt,
            screenshot_path=self.screenshot_path,
            notes=self.notes,
            version=new_version,
        )

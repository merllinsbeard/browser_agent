"""Element Registry for ID-based browser actions.

This module provides the ElementRegistry class which manages
element references by ID, enabling the agent to act on elements
without using hardcoded selectors.
"""

from dataclasses import dataclass, field

from playwright.sync_api import Locator, Page

from browser_agent.models.element import InteractiveElement


class StaleElementError(Exception):
    """Raised when attempting to use a stale element reference."""

    def __init__(self, element_ref: str, snapshot_version: int, current_version: int) -> None:
        """Initialize the stale element error.

        Args:
            element_ref: The reference ID of the stale element.
            snapshot_version: The snapshot version when the element was captured.
            current_version: The current snapshot version.
        """
        self.element_ref = element_ref
        self.snapshot_version = snapshot_version
        self.current_version = current_version
        super().__init__(
            f"Element {element_ref!r} from snapshot version {snapshot_version} "
            f"is stale (current version: {current_version}). "
            f"Re-observe the page to get fresh element references."
        )


@dataclass
class RegistryEntry:
    """A single entry in the element registry.

    Attributes:
        element: The interactive element this entry represents.
        snapshot_version: The snapshot version when this element was registered.
        selector: The CSS selector used to locate this element.
    """

    element: InteractiveElement
    snapshot_version: int
    selector: str


@dataclass
class ObservationResult:
    """Result of a page observation operation.

    Attributes:
        elements: List of interactive elements found during observation.
        snapshot_version: The version number of this snapshot.
    """

    elements: list[InteractiveElement]
    snapshot_version: int


class ElementRegistry:
    """Registry for managing element references by ID.

    The registry assigns unique reference IDs to elements during page
    observation and tracks which snapshot version each element belongs to.
    When an action is requested, the registry validates that the element
    reference is not stale and provides a Playwright Locator.

    Example:
        registry = ElementRegistry()

        # During observation, register elements
        page.goto("https://example.com")
        result = registry.register_from_page(page, version=1)

        # Get a locator for an element
        locator = registry.get_locator(page, "elem-0")

        # After page change, increment version
        registry.increment_version()
    """

    def __init__(self) -> None:
        """Initialize a new element registry."""
        self._entries: dict[str, RegistryEntry] = {}
        self._current_version: int = 0

    @property
    def current_version(self) -> int:
        """Get the current snapshot version."""
        return self._current_version

    def increment_version(self) -> int:
        """Increment the snapshot version and clear stale entries.

        Returns:
            The new version number.
        """
        self._current_version += 1
        # Clear entries from old versions
        self._entries = {
            ref: entry
            for ref, entry in self._entries.items()
            if entry.snapshot_version == self._current_version
        }
        return self._current_version

    def register_elements(
        self,
        elements: list[InteractiveElement],
        selectors: list[str],
    ) -> ObservationResult:
        """Register a batch of elements from a page observation.

        Args:
            elements: List of interactive elements to register.
            selectors: List of CSS selectors corresponding to each element.

        Returns:
            An ObservationResult containing the elements and snapshot version.

        Raises:
            ValueError: If elements and selectors have different lengths.
        """
        if len(elements) != len(selectors):
            raise ValueError(
                f"Elements ({len(elements)}) and selectors ({len(selectors)}) "
                "must have the same length"
            )

        # Clear previous entries from current version
        self._entries = {
            ref: entry
            for ref, entry in self._entries.items()
            if entry.snapshot_version != self._current_version
        }

        # Add new entries
        for i, (element, selector) in enumerate(zip(elements, selectors)):
            ref = f"elem-{i}"
            self._entries[ref] = RegistryEntry(
                element=element,
                snapshot_version=self._current_version,
                selector=selector,
            )

        return ObservationResult(
            elements=elements,
            snapshot_version=self._current_version,
        )

    def get_locator(self, page: Page, element_ref: str) -> Locator:
        """Get a Playwright Locator for an element reference.

        Args:
            page: The Playwright Page object.
            element_ref: The reference ID of the element.

        Returns:
            A Playwright Locator for the element.

        Raises:
            KeyError: If the element reference is not found.
            StaleElementError: If the element reference is from an old snapshot.
        """
        if element_ref not in self._entries:
            raise KeyError(
                f"Element reference {element_ref!r} not found in registry. "
                f"Available refs: {list(self._entries.keys())}"
            )

        entry = self._entries[element_ref]

        if entry.snapshot_version != self._current_version:
            raise StaleElementError(
                element_ref=element_ref,
                snapshot_version=entry.snapshot_version,
                current_version=self._current_version,
            )

        return page.locator(entry.selector)

    def get_element(self, element_ref: str) -> InteractiveElement:
        """Get the InteractiveElement for a reference.

        Args:
            element_ref: The reference ID of the element.

        Returns:
            The InteractiveElement.

        Raises:
            KeyError: If the element reference is not found.
            StaleElementError: If the element reference is from an old snapshot.
        """
        if element_ref not in self._entries:
            raise KeyError(
                f"Element reference {element_ref!r} not found in registry. "
                f"Available refs: {list(self._entries.keys())}"
            )

        entry = self._entries[element_ref]

        if entry.snapshot_version != self._current_version:
            raise StaleElementError(
                element_ref=element_ref,
                snapshot_version=entry.snapshot_version,
                current_version=self._current_version,
            )

        return entry.element

    def clear(self) -> None:
        """Clear all entries and reset version to 0."""
        self._entries.clear()
        self._current_version = 0

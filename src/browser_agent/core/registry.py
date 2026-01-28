"""Element Registry for ID-based browser actions.

This module provides the ElementRegistry class which manages
element references by ID, enabling the agent to act on elements
without using hardcoded selectors.
"""

from typing import Any, cast

from pydantic import BaseModel, ConfigDict
from playwright.sync_api import Locator, Page

from browser_agent.models.element import InteractiveElement


class StaleElementError(Exception):
    """Raised when attempting to use a stale element reference."""

    def __init__(self, element_ref: str, snapshot_version: int, current_version: int) -> None:
        self.element_ref = element_ref
        self.snapshot_version = snapshot_version
        self.current_version = current_version
        super().__init__(
            f"Element {element_ref!r} from snapshot version {snapshot_version} "
            f"is stale (current version: {current_version}). "
            f"Re-observe the page to get fresh element references."
        )


class RegistryEntry(BaseModel):
    """A single entry in the element registry."""

    model_config = ConfigDict(frozen=True)

    element: InteractiveElement
    snapshot_version: int
    nth: int


class ObservationResult(BaseModel):
    """Result of a page observation operation."""

    model_config = ConfigDict(frozen=True)

    elements: list[InteractiveElement]
    snapshot_version: int


class ElementRegistry:
    """Registry for managing element references by ID.

    The registry assigns unique reference IDs to elements during page
    observation and tracks which snapshot version each element belongs to.
    When an action is requested, the registry validates that the element
    reference is not stale and provides a Playwright Locator via get_by_role.
    """

    def __init__(self) -> None:
        self._entries: dict[str, RegistryEntry] = {}
        self._current_version: int = 0

    @property
    def current_version(self) -> int:
        """Get the current snapshot version."""
        return self._current_version

    def increment_version(self) -> int:
        """Increment the snapshot version, marking all existing entries as stale."""
        self._entries = {
            ref: entry
            for ref, entry in self._entries.items()
            if entry.snapshot_version == self._current_version
        }
        self._current_version += 1
        return self._current_version

    def register_elements(
        self,
        elements: list[InteractiveElement],
    ) -> ObservationResult:
        """Register a batch of elements from a page observation.

        Groups elements by (role, name) to compute nth index for disambiguation.

        Args:
            elements: List of interactive elements to register.

        Returns:
            An ObservationResult containing the elements and snapshot version.
        """
        self._entries.clear()

        # Group by (role, name) to compute nth index
        role_name_counts: dict[tuple[str, str], int] = {}

        for i, element in enumerate(elements):
            key = (element.role, element.name)
            nth = role_name_counts.get(key, 0)
            role_name_counts[key] = nth + 1

            ref = f"elem-{i}"
            self._entries[ref] = RegistryEntry(
                element=element,
                snapshot_version=self._current_version,
                nth=nth,
            )

        return ObservationResult(
            elements=elements,
            snapshot_version=self._current_version,
        )

    def get_locator(self, page: Page, element_ref: str) -> Locator:
        """Get a Playwright Locator for an element reference using get_by_role.

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

        if entry.element.name:
            return page.get_by_role(cast(Any, entry.element.role), name=entry.element.name).nth(entry.nth)
        else:
            return page.locator(f'[role="{entry.element.role}"]').nth(entry.nth)

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

"""Tests for ElementRegistry."""

from unittest.mock import MagicMock

import pytest

from browser_agent.core.registry import (
    ElementRegistry,
    ObservationResult,
    RegistryEntry,
    StaleElementError,
)
from browser_agent.models.element import BoundingBox, InteractiveElement


@pytest.fixture
def mock_page():
    """Create a mock Playwright Page object."""
    page = MagicMock()
    page.locator = MagicMock()
    return page


@pytest.fixture
def sample_elements():
    """Create sample interactive elements for testing."""
    return [
        InteractiveElement(
            ref="elem-0",
            role="button",
            name="Submit",
            aria_label="Submit form",
            placeholder="",
            value_preview="",
            bbox=BoundingBox(x=0, y=0, width=100, height=40),
        ),
        InteractiveElement(
            ref="elem-1",
            role="textbox",
            name="Email",
            aria_label="",
            placeholder="Enter email",
            value_preview="",
            bbox=BoundingBox(x=0, y=50, width=200, height=30),
        ),
    ]


@pytest.fixture
def sample_selectors():
    """Create sample CSS selectors for testing."""
    return ["button[type='submit']", "input[name='email']"]


def test_registry_initialization():
    """Test that registry initializes with correct defaults."""
    registry = ElementRegistry()

    assert registry.current_version == 0
    assert registry._entries == {}


def test_register_elements_returns_observation_result(
    sample_elements, sample_selectors
):
    """Test that register_elements returns ObservationResult."""
    registry = ElementRegistry()
    result = registry.register_elements(sample_elements, sample_selectors)

    assert isinstance(result, ObservationResult)
    assert result.elements == sample_elements
    assert result.snapshot_version == 0


def test_register_elements_assigns_ref_ids(
    sample_elements, sample_selectors
):
    """Test that register_elements assigns elem-{index} ref IDs."""
    registry = ElementRegistry()
    result = registry.register_elements(sample_elements, sample_selectors)

    # Check that elements have correct ref IDs
    assert result.elements[0].ref == "elem-0"
    assert result.elements[1].ref == "elem-1"


def test_register_elements_stores_entries(sample_elements, sample_selectors):
    """Test that register_elements stores entries correctly."""
    registry = ElementRegistry()
    registry.register_elements(sample_elements, sample_selectors)

    # Check entries are stored
    assert "elem-0" in registry._entries
    assert "elem-1" in registry._entries

    # Check entry content
    entry_0 = registry._entries["elem-0"]
    assert entry_0.element == sample_elements[0]
    assert entry_0.selector == sample_selectors[0]
    assert entry_0.snapshot_version == 0


def test_register_elements_raises_on_length_mismatch(sample_elements):
    """Test that register_elements raises ValueError when lengths differ."""
    registry = ElementRegistry()

    with pytest.raises(ValueError, match="Elements.*and selectors.*must have the same length"):
        registry.register_elements(sample_elements, ["selector1"])


def test_register_elements_clears_old_version_entries(sample_elements, sample_selectors):
    """Test that register_elements clears entries from current version before adding new ones."""
    registry = ElementRegistry()

    # First registration
    registry.register_elements(sample_elements, sample_selectors)
    assert "elem-0" in registry._entries
    assert "elem-1" in registry._entries

    # Second registration (different elements)
    new_elements = [sample_elements[0]]
    new_selectors = [sample_selectors[0]]
    registry.register_elements(new_elements, new_selectors)

    # Old elem-1 should be gone
    assert "elem-1" not in registry._entries
    # New elem-0 should be present
    assert "elem-0" in registry._entries


def test_get_locator_returns_playwright_locator(
    mock_page, sample_elements, sample_selectors
):
    """Test that get_locator returns a Playwright Locator."""
    registry = ElementRegistry()
    registry.register_elements(sample_elements, sample_selectors)

    locator = registry.get_locator(mock_page, "elem-0")

    assert locator == mock_page.locator.return_value
    mock_page.locator.assert_called_once_with(sample_selectors[0])


def test_get_locator_raises_on_unknown_ref(mock_page):
    """Test that get_locator raises KeyError for unknown ref."""
    registry = ElementRegistry()

    with pytest.raises(KeyError, match="Element reference.*not found"):
        registry.get_locator(mock_page, "elem-999")


def test_get_locator_raises_on_stale_element(mock_page, sample_elements, sample_selectors):
    """Test that get_locator raises StaleElementError for stale elements."""
    registry = ElementRegistry()
    registry.register_elements(sample_elements, sample_selectors)

    # Increment version to make elements stale
    registry.increment_version()

    with pytest.raises(StaleElementError) as exc_info:
        registry.get_locator(mock_page, "elem-0")

    assert exc_info.value.element_ref == "elem-0"
    assert exc_info.value.snapshot_version == 0
    assert exc_info.value.current_version == 1


def test_get_element_returns_interactive_element(sample_elements, sample_selectors):
    """Test that get_element returns the InteractiveElement."""
    registry = ElementRegistry()
    registry.register_elements(sample_elements, sample_selectors)

    element = registry.get_element("elem-0")

    assert element == sample_elements[0]
    assert element.name == "Submit"


def test_get_element_raises_on_unknown_ref(sample_elements, sample_selectors):
    """Test that get_element raises KeyError for unknown ref."""
    registry = ElementRegistry()
    registry.register_elements(sample_elements, sample_selectors)

    with pytest.raises(KeyError, match="Element reference.*not found"):
        registry.get_element("elem-999")


def test_get_element_raises_on_stale_element(sample_elements, sample_selectors):
    """Test that get_element raises StaleElementError for stale elements."""
    registry = ElementRegistry()
    registry.register_elements(sample_elements, sample_selectors)

    # Increment version to make elements stale
    registry.increment_version()

    with pytest.raises(StaleElementError) as exc_info:
        registry.get_element("elem-0")

    assert exc_info.value.element_ref == "elem-0"
    assert exc_info.value.snapshot_version == 0
    assert exc_info.value.current_version == 1


def test_increment_version_increments_counter(sample_elements, sample_selectors):
    """Test that increment_version increments the version counter."""
    registry = ElementRegistry()
    registry.register_elements(sample_elements, sample_selectors)

    assert registry.current_version == 0

    new_version = registry.increment_version()
    assert new_version == 1
    assert registry.current_version == 1

    new_version = registry.increment_version()
    assert new_version == 2
    assert registry.current_version == 2


def test_increment_version_clears_old_entries(sample_elements, sample_selectors):
    """Test that increment_version keeps entries but marks them as stale."""
    registry = ElementRegistry()

    # Register elements at version 0
    registry.register_elements(sample_elements, sample_selectors)
    assert "elem-0" in registry._entries
    assert "elem-1" in registry._entries

    # Increment to version 1
    registry.increment_version()

    # Entries are still present but now stale (snapshot_version=0 < current_version=1)
    assert "elem-0" in registry._entries
    assert "elem-1" in registry._entries
    assert registry._entries["elem-0"].snapshot_version == 0
    assert registry.current_version == 1


def test_increment_version_keeps_current_version_entries(sample_elements, sample_selectors):
    """Test that increment_version keeps entries from current version."""
    registry = ElementRegistry()

    # Register elements at version 0
    registry.register_elements(sample_elements, sample_selectors)

    # Manually add an entry at version 1 (simulating re-observation)
    registry._current_version = 1
    registry._entries["elem-new"] = RegistryEntry(
        element=sample_elements[0],
        snapshot_version=1,
        selector="button.new",
    )

    # Increment should keep the version 1 entry
    registry.increment_version()
    assert registry.current_version == 2
    assert "elem-new" in registry._entries


def test_clear_resets_registry_state(sample_elements, sample_selectors):
    """Test that clear resets all registry state."""
    registry = ElementRegistry()
    registry.register_elements(sample_elements, sample_selectors)
    registry.increment_version()

    # Verify state before clear
    assert registry.current_version == 1
    assert len(registry._entries) > 0

    # Clear
    registry.clear()

    # Verify state after clear
    assert registry.current_version == 0
    assert registry._entries == {}


def test_current_version_property():
    """Test that current_version property returns the version."""
    registry = ElementRegistry()

    assert registry.current_version == 0

    registry._current_version = 5
    assert registry.current_version == 5


def test_multiple_observation_cycles(sample_elements, sample_selectors):
    """Test multiple register/increment cycles."""
    registry = ElementRegistry()

    # First observation
    result1 = registry.register_elements(sample_elements, sample_selectors)
    assert result1.snapshot_version == 0
    assert registry.get_element("elem-0") == sample_elements[0]

    # Increment version
    registry.increment_version()

    # Second observation with same elements
    result2 = registry.register_elements(sample_elements, sample_selectors)
    assert result2.snapshot_version == 1
    assert registry.get_element("elem-0") == sample_elements[0]

    # Third observation after increment
    registry.increment_version()
    result3 = registry.register_elements([sample_elements[0]], [sample_selectors[0]])
    assert result3.snapshot_version == 2
    assert "elem-0" in registry._entries
    assert "elem-1" not in registry._entries


def test_stale_element_error_message():
    """Test that StaleElementError has a helpful error message."""
    error = StaleElementError("elem-5", 3, 7)

    assert str(error) == (
        "Element 'elem-5' from snapshot version 3 is stale (current version: 7). "
        "Re-observe the page to get fresh element references."
    )

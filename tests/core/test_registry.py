"""Tests for ElementRegistry."""

from unittest.mock import MagicMock

import pytest

from browser_agent.core.registry import ElementRegistry, StaleElementError
from browser_agent.models.element import InteractiveElement


@pytest.fixture
def elements() -> list[InteractiveElement]:
    return [
        InteractiveElement(ref="elem-0", role="button", name="Submit"),
        InteractiveElement(ref="elem-1", role="link", name="Home"),
        InteractiveElement(ref="elem-2", role="button", name="Submit"),  # duplicate role+name
        InteractiveElement(ref="elem-3", role="textbox", name=""),  # empty name
    ]


class TestElementRegistry:
    def test_initial_version(self, registry: ElementRegistry) -> None:
        assert registry.current_version == 0

    def test_register_elements(
        self, registry: ElementRegistry, elements: list[InteractiveElement]
    ) -> None:
        result = registry.register_elements(elements)
        assert result.snapshot_version == 0
        assert len(result.elements) == len(elements)

    def test_increment_version(self, registry: ElementRegistry) -> None:
        assert registry.current_version == 0
        new_version = registry.increment_version()
        assert new_version == 1
        assert registry.current_version == 1

    def test_get_element(
        self, registry: ElementRegistry, elements: list[InteractiveElement]
    ) -> None:
        registry.register_elements(elements)
        elem = registry.get_element("elem-0")
        assert elem.role == "button"
        assert elem.name == "Submit"

    def test_get_element_not_found(self, registry: ElementRegistry) -> None:
        with pytest.raises(KeyError, match="not found"):
            registry.get_element("elem-999")

    def test_stale_element_after_increment(
        self, registry: ElementRegistry, elements: list[InteractiveElement]
    ) -> None:
        registry.register_elements(elements)
        registry.increment_version()
        # increment_version keeps entries but bumps version, so they become stale
        with pytest.raises(StaleElementError):
            registry.get_element("elem-0")

    def test_stale_after_version_change(
        self, registry: ElementRegistry, elements: list[InteractiveElement]
    ) -> None:
        registry.register_elements(elements)
        # Manually increment without re-registering
        # increment_version keeps entries with current version before incrementing
        # So entries at version 0 survive, but their snapshot_version (0) != new current (1)
        registry._current_version = 1  # Simulate version change without clearing
        with pytest.raises(StaleElementError) as exc_info:
            registry.get_element("elem-0")
        assert exc_info.value.element_ref == "elem-0"
        assert exc_info.value.snapshot_version == 0
        assert exc_info.value.current_version == 1

    def test_get_locator_with_name(
        self, registry: ElementRegistry, elements: list[InteractiveElement]
    ) -> None:
        registry.register_elements(elements)
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_page.get_by_role.return_value.nth.return_value = mock_locator

        locator = registry.get_locator(mock_page, "elem-0")

        mock_page.get_by_role.assert_called_once()
        call_args = mock_page.get_by_role.call_args
        assert call_args.kwargs["name"] == "Submit"
        mock_page.get_by_role.return_value.nth.assert_called_once_with(0)
        assert locator == mock_locator

    def test_get_locator_empty_name_uses_css(
        self, registry: ElementRegistry, elements: list[InteractiveElement]
    ) -> None:
        registry.register_elements(elements)
        mock_page = MagicMock()
        mock_locator = MagicMock()
        mock_page.locator.return_value.nth.return_value = mock_locator

        locator = registry.get_locator(mock_page, "elem-3")

        mock_page.locator.assert_called_once_with("[role=textbox]")
        mock_page.locator.return_value.nth.assert_called_once_with(0)
        assert locator == mock_locator

    def test_nth_disambiguation(
        self, registry: ElementRegistry, elements: list[InteractiveElement]
    ) -> None:
        registry.register_elements(elements)
        mock_page = MagicMock()
        mock_locator_0 = MagicMock()
        mock_locator_1 = MagicMock()
        mock_page.get_by_role.return_value.nth.side_effect = [
            mock_locator_0,
            mock_locator_1,
        ]

        # elem-0 is first "Submit" button (nth=0)
        registry.get_locator(mock_page, "elem-0")
        first_nth_call = mock_page.get_by_role.return_value.nth.call_args_list[0]
        assert first_nth_call[0][0] == 0

        # elem-2 is second "Submit" button (nth=1)
        registry.get_locator(mock_page, "elem-2")
        second_nth_call = mock_page.get_by_role.return_value.nth.call_args_list[1]
        assert second_nth_call[0][0] == 1

    def test_get_locator_not_found(self, registry: ElementRegistry) -> None:
        mock_page = MagicMock()
        with pytest.raises(KeyError, match="not found"):
            registry.get_locator(mock_page, "elem-999")

    def test_clear(
        self, registry: ElementRegistry, elements: list[InteractiveElement]
    ) -> None:
        registry.register_elements(elements)
        registry.increment_version()
        registry.clear()
        assert registry.current_version == 0
        with pytest.raises(KeyError):
            registry.get_element("elem-0")

    def test_version_tracking(
        self, registry: ElementRegistry, elements: list[InteractiveElement]
    ) -> None:
        result1 = registry.register_elements(elements)
        assert result1.snapshot_version == 0

        registry.increment_version()
        result2 = registry.register_elements(elements)
        assert result2.snapshot_version == 1


class TestStaleElementError:
    def test_error_message(self) -> None:
        err = StaleElementError(
            element_ref="elem-0", snapshot_version=0, current_version=2
        )
        assert "elem-0" in str(err)
        assert "version 0" in str(err)
        assert "version: 2" in str(err)
        assert err.element_ref == "elem-0"
        assert err.snapshot_version == 0
        assert err.current_version == 2

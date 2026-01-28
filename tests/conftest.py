"""Shared test fixtures for browser_agent tests."""

import pytest

from browser_agent.models.element import BoundingBox, InteractiveElement
from browser_agent.models.snapshot import PageSnapshot
from browser_agent.core.registry import ElementRegistry


@pytest.fixture
def sample_bbox() -> BoundingBox:
    return BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)


@pytest.fixture
def sample_element() -> InteractiveElement:
    return InteractiveElement(ref="elem-0", role="button", name="Submit")


@pytest.fixture
def sample_snapshot(sample_element: InteractiveElement) -> PageSnapshot:
    return PageSnapshot(
        url="https://example.com",
        title="Example Domain",
        interactive_elements=[sample_element],
        visible_text_excerpt="Example text",
    )


@pytest.fixture
def registry() -> ElementRegistry:
    return ElementRegistry()

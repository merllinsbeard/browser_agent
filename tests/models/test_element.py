"""Tests for element models (BoundingBox, InteractiveElement)."""

import pytest
from pydantic import ValidationError

from browser_agent.models.element import BoundingBox, InteractiveElement


class TestBoundingBox:
    def test_creation(self) -> None:
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        assert bbox.x == 10.0
        assert bbox.y == 20.0
        assert bbox.width == 100.0
        assert bbox.height == 50.0

    def test_zero_dimensions_allowed(self) -> None:
        bbox = BoundingBox(x=0.0, y=0.0, width=0.0, height=0.0)
        assert bbox.width == 0.0
        assert bbox.height == 0.0

    def test_negative_width_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must be non-negative"):
            BoundingBox(x=0.0, y=0.0, width=-1.0, height=10.0)

    def test_negative_height_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must be non-negative"):
            BoundingBox(x=0.0, y=0.0, width=10.0, height=-5.0)

    def test_negative_x_y_allowed(self) -> None:
        bbox = BoundingBox(x=-10.0, y=-20.0, width=100.0, height=50.0)
        assert bbox.x == -10.0
        assert bbox.y == -20.0

    def test_frozen_immutability(self) -> None:
        bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)
        with pytest.raises(ValidationError):
            bbox.x = 999.0  # type: ignore[misc]


class TestInteractiveElement:
    def test_creation_with_all_fields(self) -> None:
        bbox = BoundingBox(x=0.0, y=0.0, width=50.0, height=30.0)
        elem = InteractiveElement(
            ref="elem-0",
            role="button",
            name="Submit",
            aria_label="Submit form",
            placeholder=None,
            value_preview="Click me",
            bbox=bbox,
        )
        assert elem.ref == "elem-0"
        assert elem.role == "button"
        assert elem.name == "Submit"
        assert elem.aria_label == "Submit form"
        assert elem.value_preview == "Click me"
        assert elem.bbox is not None
        assert elem.bbox.width == 50.0

    def test_empty_name_allowed(self) -> None:
        elem = InteractiveElement(ref="elem-0", role="button", name="")
        assert elem.name == ""

    def test_name_defaults_to_empty(self) -> None:
        elem = InteractiveElement(ref="elem-0", role="button")
        assert elem.name == ""

    def test_optional_fields_default_none(self) -> None:
        elem = InteractiveElement(ref="elem-0", role="link")
        assert elem.aria_label is None
        assert elem.placeholder is None
        assert elem.value_preview is None
        assert elem.bbox is None

    def test_frozen_immutability(self) -> None:
        elem = InteractiveElement(ref="elem-0", role="button", name="OK")
        with pytest.raises(ValidationError):
            elem.name = "Changed"  # type: ignore[misc]

    def test_ref_and_role_required(self) -> None:
        with pytest.raises(ValidationError):
            InteractiveElement(role="button")  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            InteractiveElement(ref="elem-0")  # type: ignore[call-arg]

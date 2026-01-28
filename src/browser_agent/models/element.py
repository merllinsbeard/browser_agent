"""Element models for page interaction.

This module defines the InteractiveElement model which represents
an interactive element on a web page.
"""

from pydantic import BaseModel, ConfigDict, field_validator


class BoundingBox(BaseModel):
    """Bounding box of an element on the page.

    Attributes:
        x: X coordinate in pixels.
        y: Y coordinate in pixels.
        width: Width in pixels (must be non-negative).
        height: Height in pixels (must be non-negative).
    """

    model_config = ConfigDict(frozen=True)

    x: float
    y: float
    width: float
    height: float

    @field_validator("width", "height")
    @classmethod
    def must_be_non_negative(cls, v: float, info: object) -> float:
        """Validate that dimensions are non-negative."""
        if v < 0:
            raise ValueError(f"must be non-negative, got {v}")
        return v


class InteractiveElement(BaseModel):
    """An interactive element on a web page.

    This represents a clickable, typeable, or otherwise interactive
    element that the agent can act upon. Elements are identified
    by a unique ref ID assigned by the ElementRegistry.

    Attributes:
        ref: Unique reference ID for this element (assigned by registry).
        role: ARIA role of the element (button, link, textbox, etc.).
        name: Accessible name of the element (may be empty).
        aria_label: ARIA label attribute (if present).
        placeholder: Placeholder text for inputs (if applicable).
        value_preview: Preview of the current value (truncated if long).
        bbox: Bounding box of the element on the page.
    """

    model_config = ConfigDict(frozen=True)

    ref: str
    role: str
    name: str = ""

    @field_validator("ref", "role")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        """Validate that ref and role are not empty strings."""
        if not v:
            raise ValueError("must not be empty")
        return v

    aria_label: str | None = None
    placeholder: str | None = None
    value_preview: str | None = None
    bbox: BoundingBox | None = None

"""Element models for page interaction.

This module defines the InteractiveElement model which represents
an interactive element on a web page.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class BoundingBox:
    """Bounding box of an element on the page.

    Attributes:
        x: X coordinate in pixels.
        y: Y coordinate in pixels.
        width: Width in pixels.
        height: Height in pixels.
    """

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class InteractiveElement:
    """An interactive element on a web page.

    This represents a clickable, typeable, or otherwise interactive
    element that the agent can act upon. Elements are identified
    by a unique ref ID assigned by the ElementRegistry.

    Attributes:
        ref: Unique reference ID for this element (assigned by registry).
        role: ARIA role of the element (button, link, textbox, etc.).
        name: Accessible name of the element.
        aria_label: ARIA label attribute (if present).
        placeholder: Placeholder text for inputs (if applicable).
        value_preview: Preview of the current value (truncated if long).
        bbox: Bounding box of the element on the page.
    """

    ref: str
    role: str
    name: str
    aria_label: str | None = None
    placeholder: str | None = None
    value_preview: str | None = None
    bbox: BoundingBox | None = None

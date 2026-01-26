"""Browser Agent tools."""

from browser_agent.tools.actions import (
    click,
    done,
    extract,
    navigate,
    press,
    scroll,
    type_,
    wait,
)
from browser_agent.tools.hybrid_observe import (
    hybrid_observe,
    needs_vision_fallback,
)
from browser_agent.tools.observe import browser_observe
from browser_agent.tools.screenshot import capture_screenshot

__all__ = [
    "browser_observe",
    "capture_screenshot",
    "hybrid_observe",
    "needs_vision_fallback",
    "click",
    "type_",
    "press",
    "scroll",
    "navigate",
    "wait",
    "extract",
    "done",
]

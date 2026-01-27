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
from browser_agent.tools.observe import browser_observe
from browser_agent.tools.screenshot import capture_screenshot

__all__ = [
    "browser_observe",
    "capture_screenshot",
    "click",
    "type_",
    "press",
    "scroll",
    "navigate",
    "wait",
    "extract",
    "done",
]

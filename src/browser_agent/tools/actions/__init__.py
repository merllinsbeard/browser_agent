"""Browser action tools for element interaction."""

from browser_agent.tools.actions.click import click
from browser_agent.tools.actions.done import done
from browser_agent.tools.actions.extract import extract
from browser_agent.tools.actions.navigate import navigate
from browser_agent.tools.actions.press import press
from browser_agent.tools.actions.scroll import scroll
# Import from type.py but export as type_ to avoid shadowing built-in
from browser_agent.tools.actions.type import type_ as type_func
type_ = type_func
from browser_agent.tools.actions.wait import wait

__all__ = [
    "click",
    "type_",
    "press",
    "scroll",
    "navigate",
    "wait",
    "extract",
    "done",
]

"""Action types for browser automation.

This module defines the Action enum representing all possible actions
the browser agent can perform.
"""

from enum import Enum


class Action(str, Enum):
    """Types of actions the browser agent can execute.

    Each action corresponds to a specific tool the agent can use
    to interact with the browser.
    """

    CLICK = "CLICK"
    TYPE = "TYPE"
    PRESS = "PRESS"
    SCROLL = "SCROLL"
    NAVIGATE = "NAVIGATE"
    WAIT = "WAIT"
    EXTRACT = "EXTRACT"
    DONE = "DONE"

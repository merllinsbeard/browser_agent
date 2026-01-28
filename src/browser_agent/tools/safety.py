"""Safety checks for browser tools.

Deterministic keyword-based safety layer that detects destructive actions
and requires user confirmation before proceeding. This runs at the tool
level (not the LLM level) — the agent cannot bypass it.
"""

import asyncio
import string

from browser_agent.core.logging import logEvent, logForDebugging

_DESTRUCTIVE_KEYWORDS = frozenset({
    "delete",
    "remove",
    "spam",
    "submit",
    "payment",
    "checkout",
    "confirm",
    "purchase",
    "buy",
    "order",
    "send",
    "apply",
    "trash",
})


def is_destructive_action(action_description: str) -> bool:
    """Check if an action description contains destructive keywords.

    This is a synchronous, deterministic check — no LLM involved.
    Strips punctuation from each word before matching so that
    "Delete?" and "Submit!" are correctly detected.

    Args:
        action_description: Description of the action (e.g., element role + name).

    Returns:
        True if the action matches a destructive keyword, False otherwise.
    """
    words = action_description.lower().split()
    stripped = [w.strip(string.punctuation) for w in words]
    result = any(word in _DESTRUCTIVE_KEYWORDS for word in stripped)
    logForDebugging(
        f"Safety check: {action_description!r} -> {'DESTRUCTIVE' if result else 'safe'}",
        extra={"matched_words": [w for w in stripped if w in _DESTRUCTIVE_KEYWORDS]},
    )
    return result


async def ask_user_confirmation(action_description: str, auto_approve: bool = False) -> bool:
    """Ask the user to confirm a destructive action.

    Prints the action description and prompts yes/no in the terminal.
    Blocks until the user responds.

    Args:
        action_description: Human-readable description of the action.
        auto_approve: If True, skip the prompt and return True immediately.

    Returns:
        True if the user confirms (or auto_approve is True), False otherwise.
    """
    if auto_approve:
        logEvent("safety_auto_approve", {"action": action_description})
        return True

    from rich.console import Console
    from rich.prompt import Confirm

    console = Console()

    def _prompt() -> bool:
        try:
            console.print(
                f"\n[bold red]⚠ Safety Check:[/bold red] "
                f"The agent wants to interact with: [bold]{action_description}[/bold]"
            )
            return Confirm.ask("[bold yellow]Allow this action?[/bold yellow]", default=False)
        except (EOFError, KeyboardInterrupt):
            return False

    result = await asyncio.to_thread(_prompt)
    if result:
        logEvent("safety_user_approved", {"action": action_description})
    else:
        logEvent("safety_user_denied", {"action": action_description})
    return result

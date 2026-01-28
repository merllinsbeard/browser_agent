"""Safety checks for browser tools.

Deterministic keyword-based safety layer that detects destructive actions
and requires user confirmation before proceeding. This runs at the tool
level (not the LLM level) — the agent cannot bypass it.
"""

import asyncio

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
})


def is_destructive_action(action_description: str) -> bool:
    """Check if an action description contains destructive keywords.

    This is a synchronous, deterministic check — no LLM involved.

    Args:
        action_description: Description of the action (e.g., element role + name).

    Returns:
        True if the action matches a destructive keyword, False otherwise.
    """
    words = action_description.lower().split()
    return any(word in _DESTRUCTIVE_KEYWORDS for word in words)


async def ask_user_confirmation(action_description: str) -> bool:
    """Ask the user to confirm a destructive action.

    Prints the action description and prompts yes/no in the terminal.
    Blocks until the user responds.

    Args:
        action_description: Human-readable description of the action.

    Returns:
        True if the user confirms, False otherwise.
    """
    from rich.console import Console
    from rich.prompt import Confirm

    console = Console()

    def _prompt() -> bool:
        console.print(
            f"\n[bold red]⚠ Safety Check:[/bold red] "
            f"The agent wants to interact with: [bold]{action_description}[/bold]"
        )
        return Confirm.ask("[bold yellow]Allow this action?[/bold yellow]", default=False)

    return await asyncio.to_thread(_prompt)

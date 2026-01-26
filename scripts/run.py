#!/usr/bin/env python3
"""Interactive run script for browser-agent."""

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.panel import Panel

console = Console()


def main() -> None:
    """Launch the browser agent interactively."""
    console.print(Panel.fit(
        "[bold cyan]Browser Agent[/bold cyan]\n"
        "[dim]Autonomous AI browser controller[/dim]",
        title="Welcome"
    ))

    # TODO: Implement full agent launch
    console.print("\n[yellow]Agent implementation in progress...[/yellow]")
    console.print("This will be the main interactive entry point once implementation is complete.")


if __name__ == "__main__":
    main()

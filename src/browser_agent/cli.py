"""CLI entry point for browser-agent."""

import argparse
from pathlib import Path

from rich.console import Console

from browser_agent.core.browser import launch_persistent_context
from playwright.sync_api import sync_playwright

console = Console()

DEFAULT_SESSION_DIR = Path.home() / ".browser-agent" / "session"


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Browser Agent - Autonomous AI browser controller"
    )
    parser.add_argument(
        "--session-dir",
        type=str,
        default=str(DEFAULT_SESSION_DIR),
        help=f"Directory for persistent session data (default: {DEFAULT_SESSION_DIR})",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (default: visible browser)",
    )

    args = parser.parse_args()

    # For now, just show a message and test browser launch
    console.print("[bold cyan]Browser Agent[/bold cyan] - Autonomous AI browser controller")
    console.print(f"Session directory: [dim]{args.session_dir}[/dim]")
    console.print("Use [bold]scripts/run.py[/bold] to run the agent interactively")

    # Test browser launch
    with sync_playwright() as p:
        console.print("\n[yellow]Launching browser...[/yellow]")
        context = launch_persistent_context(
            p,
            user_data_dir=args.session_dir,
            headless=args.headless,
        )
        console.print("[green]Browser launched successfully![/green]")
        console.print("[dim]Press Ctrl+C to close...[/dim]")

        try:
            # Keep browser open until user interrupts
            context.wait_for_event("close", timeout=0)
        except KeyboardInterrupt:
            console.print("\n[yellow]Closing browser...[/yellow]")
            context.close()
            console.print("[green]Done.[/green]")


if __name__ == "__main__":
    main()

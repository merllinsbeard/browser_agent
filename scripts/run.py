#!/usr/bin/env python3
"""Interactive run script for browser-agent."""

import argparse
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from playwright.sync_api import sync_playwright

from browser_agent.agents import PlannerAgent, NavigatorAgent, SafetyAgent
from browser_agent.core import (
    ContextTracker,
    ElementRegistry,
    StuckDetector,
    launch_persistent_context,
)
from rich.console import Console
from rich.panel import Panel

console = Console()


def get_session_dir() -> Path:
    """Get the default session directory."""
    return Path.home() / ".browser-agent" / "session"


def main() -> None:
    """Launch the browser agent interactively."""
    parser = argparse.ArgumentParser(
        description="Browser Agent - Autonomous AI browser controller"
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="The task to perform (if not provided, will prompt interactively)",
    )
    parser.add_argument(
        "--session-dir",
        type=Path,
        default=get_session_dir(),
        help="Directory for persistent browser session (default: ~/.browser-agent/session)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (default: visible browser)",
    )

    args = parser.parse_args()

    # Get task from command line or prompt
    task = args.task
    if not task:
        console.print(Panel.fit(
            "[bold cyan]Browser Agent[/bold cyan]\n"
            "[dim]Autonomous AI browser controller[/dim]",
            title="Welcome"
        ))
        task = console.input("\n[bold yellow]Enter a task for the agent:[/bold yellow] ")
        if not task.strip():
            console.print("[red]No task provided. Exiting.[/red]")
            return

    # Display the task
    console.print(f"\n[bold green]Task:[/bold green] {task}")

    # Initialize components
    session_dir = args.session_dir
    session_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[dim]Session directory: {session_dir}[/dim]")
    console.print(f"[dim]Headless mode: {args.headless}[/dim]")

    # Launch browser
    with sync_playwright() as p:
        try:
            console.print("\n[yellow]Launching browser...[/yellow]")
            context = launch_persistent_context(
                p,
                user_data_dir=session_dir,
                headless=args.headless,
            )

            # Get or create the page
            pages = context.pages
            if pages:
                page = pages[0]
            else:
                page = context.new_page()

            console.print("[green]Browser launched successfully![/green]")

            # Initialize agent components
            registry = ElementRegistry()
            context_tracker = ContextTracker()
            stuck_detector = StuckDetector()
            safety_agent = SafetyAgent(console)

            # Create planner and navigator
            planner = PlannerAgent()
            navigator = NavigatorAgent(page, registry, console)

            # TODO: Implement full agent orchestration
            # This is a placeholder for the complete implementation
            console.print("\n[yellow]Agent components initialized.[/yellow]")
            console.print("[dim]Full orchestration will be implemented in upcoming user stories.[/dim]")

            # Keep browser open for observation
            if not args.headless:
                console.print("\n[dim]Press Ctrl+C to close the browser...[/dim]")
                import time
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Shutting down...[/yellow]")

            context.close()

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return


if __name__ == "__main__":
    main()

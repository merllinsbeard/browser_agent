#!/usr/bin/env python3
"""Interactive run script for browser-agent using OpenAI Agents SDK."""

import argparse
import asyncio
import shutil
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents import RunConfig, Runner
from agents.exceptions import MaxTurnsExceeded
from playwright.async_api import async_playwright

from browser_agent.agents import create_navigator_agent, create_planner_agent
from browser_agent.core import (
    ElementRegistry,
    launch_persistent_context_async,
    setup_openrouter_for_sdk,
)
from browser_agent.tools import create_browser_tools
from rich.console import Console
from rich.panel import Panel

console = Console()


def get_session_dir() -> Path:
    """Get the default session directory."""
    return Path.home() / ".browser-agent" / "session"


async def main() -> None:
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
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve all actions without confirmation (use with caution)",
    )
    parser.add_argument(
        "--clean-cache",
        action="store_true",
        help="Clear the browser session cache before starting",
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

    # Session directory setup
    session_dir = args.session_dir
    if args.clean_cache and session_dir.exists():
        console.print(f"[yellow]Cleaning session cache: {session_dir}[/yellow]")
        shutil.rmtree(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[dim]Session directory: {session_dir}[/dim]")
    console.print(f"[dim]Headless mode: {args.headless}[/dim]")
    if args.auto_approve:
        console.print("[yellow][dim]Auto-approve mode: ENABLED[/dim][/yellow]")

    # Configure SDK LLM client (returns OpenAIProvider for RunConfig)
    model_provider = setup_openrouter_for_sdk()

    # Launch browser (async)
    pw = await async_playwright().start()
    try:
        console.print("\n[yellow]Launching browser...[/yellow]")
        context = await launch_persistent_context_async(
            pw,
            user_data_dir=session_dir,
            headless=args.headless,
        )

        # Get or create the page
        pages = context.pages
        page = pages[0] if pages else await context.new_page()

        console.print("[green]Browser launched successfully![/green]")

        # Initialize agent components
        registry = ElementRegistry()
        tools = create_browser_tools(page, registry)

        # Create agents: Navigator (has tools) -> Planner (hands off to Navigator)
        navigator = create_navigator_agent(tools)
        planner = create_planner_agent(navigator)

        # Run the ReAct loop
        console.print("\n[yellow]Starting agent...[/yellow]")
        try:
            run_config = RunConfig(model_provider=model_provider)
            result = await Runner.run(planner, task, max_turns=30, run_config=run_config)
            console.print("\n")
            console.print(Panel(
                f"[bold green]Task Complete![/bold green]\n\n"
                f"[dim]{result.final_output}[/dim]",
                title="Summary"
            ))
        except MaxTurnsExceeded:
            console.print("\n")
            console.print(Panel(
                "[bold yellow]Agent reached the maximum turn limit (30 turns).[/bold yellow]\n\n"
                "The task may be partially complete. Try breaking it into smaller steps "
                "or increasing the turn limit.",
                title="Turn Limit Reached",
                border_style="yellow"
            ))

        # Keep browser open for observation
        if not args.headless:
            console.print("\n[dim]Press Ctrl+C to close the browser...[/dim]")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Shutting down...[/yellow]")

        await context.close()

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
    finally:
        await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())

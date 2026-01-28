#!/usr/bin/env python3
"""Demo script for browser-agent using OpenAI Agents SDK.

This script demonstrates the autonomous browser AI agent completing a novel task.
The agent will:
1. Launch a visible browser
2. Create an execution plan (Planner agent)
3. Hand off to Navigator agent for browser control
4. Navigate, observe, and interact with web pages
5. Handle any errors that occur
6. Display a completion report

Usage:
    uv run python scripts/demo.py [--task "your task here"] [--headless]
"""

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
from browser_agent.core.logging import ErrorIds, logError, logEvent
from browser_agent.tools import create_browser_tools
from rich.console import Console
from rich.panel import Panel

console = Console()

DEFAULT_DEMO_TASK = "Go to example.com and tell me what the page title is"
DEMO_SESSION_DIR = Path.home() / ".browser-agent" / "demo-session"


async def run_demo(
    task: str,
    headless: bool = False,
    auto_approve: bool = False,
    clean_cache: bool = False,
) -> None:
    """Run the browser agent demo.

    Args:
        task: The task for the agent to perform.
        headless: Whether to run in headless mode.
        auto_approve: Whether to auto-approve all actions.
        clean_cache: Whether to clear the session cache before starting.
    """
    session_dir = DEMO_SESSION_DIR

    if clean_cache and session_dir.exists():
        console.print(f"[yellow]Cleaning demo session cache: {session_dir}[/yellow]")
        shutil.rmtree(session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold green]Task:[/bold green] {task}")
    console.print(f"[dim]Session directory: {session_dir}[/dim]")
    console.print(f"[dim]Headless mode: {headless}[/dim]")
    if auto_approve:
        console.print("[yellow][dim]Auto-approve mode: ENABLED[/dim][/yellow]")

    # Configure SDK LLM client (returns OpenAIProvider for RunConfig)
    model_provider = setup_openrouter_for_sdk()

    # Launch browser (async)
    pw = await async_playwright().start()
    context = None
    try:
        console.print("\n[yellow]Launching browser...[/yellow]")
        context = await launch_persistent_context_async(
            pw,
            user_data_dir=session_dir,
            headless=headless,
        )

        # Get or create the page
        pages = context.pages
        page = pages[0] if pages else await context.new_page()

        console.print("[green]Browser launched successfully![/green]")

        # Initialize agent components
        registry = ElementRegistry()
        tools = create_browser_tools(page, registry, auto_approve=auto_approve)

        # Create agents: Navigator (has tools) -> Planner (hands off to Navigator)
        navigator = create_navigator_agent(tools)
        planner = create_planner_agent(navigator)

        # Run the ReAct loop
        logEvent("demo_start", {"task": task})
        console.print("\n[yellow]Starting agent...[/yellow]")
        try:
            run_config = RunConfig(model_provider=model_provider)
            result = await Runner.run(planner, task, max_turns=30, run_config=run_config)
            logEvent("demo_complete", {"task": task, "output": str(result.final_output)[:200]})
            console.print("\n")
            console.print(Panel(
                f"[bold green]Demo Complete![/bold green]\n\n"
                f"[dim]{result.final_output}[/dim]",
                title="Summary",
            ))
        except MaxTurnsExceeded:
            logEvent("demo_max_turns", {"task": task, "max_turns": 30})
            console.print("\n")
            console.print(Panel(
                "[bold yellow]Agent reached the maximum turn limit (30 turns).[/bold yellow]\n\n"
                "The task may be partially complete. Try breaking it into smaller steps "
                "or increasing the turn limit.",
                title="Turn Limit Reached",
                border_style="yellow",
            ))

        # Keep browser open for observation
        if not headless:
            console.print("\n[dim]Press Ctrl+C to close the browser...[/dim]")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                console.print("\n[yellow]Shutting down...[/yellow]")

    except Exception as e:
        logError(ErrorIds.UNEXPECTED_ERROR, f"Demo script error: {e}", exc_info=True)
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
    finally:
        if context is not None:
            await context.close()
        await pw.stop()


async def main() -> None:
    """Main demo entry point."""
    parser = argparse.ArgumentParser(
        description="Browser Agent Demo - Autonomous AI browser controller"
    )
    parser.add_argument(
        "--task",
        type=str,
        default=DEFAULT_DEMO_TASK,
        help=f"The task for the agent to perform (default: {DEFAULT_DEMO_TASK})",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (default: visible browser for demo)",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve all actions without confirmation",
    )
    parser.add_argument(
        "--clean-cache",
        action="store_true",
        help="Clear the demo session cache before starting",
    )

    args = parser.parse_args()

    # Display demo banner
    console.print(Panel.fit(
        "[bold cyan]Browser Agent Demo[/bold cyan]\n"
        "[dim]Autonomous AI browser controller demonstration[/dim]\n\n"
        "[yellow]Architecture:[/yellow]\n"
        "  Planner Agent -> Navigator Agent (handoff)\n\n"
        "[yellow]Features demonstrated:[/yellow]\n"
        "  - ReAct loop via OpenAI Agents SDK\n"
        "  - Dynamic task planning with Planner agent\n"
        "  - Autonomous browser control with Navigator agent\n"
        "  - ARIA-based element observation (no CSS selectors)\n"
        "  - Destructive action safety checks\n"
        "  - Error recovery and adaptation",
        title="Demo",
        border_style="cyan",
    ))

    console.print("\n[dim]The agent will perform a novel task (not pre-scripted).[/dim]")
    console.print("[dim]Watch as it plans, executes, and adapts to the page.[/dim]\n")

    await run_demo(
        task=args.task,
        headless=args.headless,
        auto_approve=args.auto_approve,
        clean_cache=args.clean_cache,
    )


if __name__ == "__main__":
    asyncio.run(main())

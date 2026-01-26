#!/usr/bin/env python3
"""Demo script for browser-agent.

This script demonstrates the autonomous browser AI agent completing a novel task.
The agent will:
1. Launch a visible browser
2. Create an execution plan
3. Navigate to a website
4. Extract information
5. Handle any errors that occur
6. Display a completion report

Usage:
    uv run python scripts/demo.py [--task "your task here"] [--headless]
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def run_demo(task: str, headless: bool = False, auto_approve: bool = False) -> int:
    """Run the browser agent demo.

    Args:
        task: The task for the agent to perform.
        headless: Whether to run in headless mode.
        auto_approve: Whether to auto-approve all actions.

    Returns:
        Exit code from the agent run.
    """
    # Build command to run run.py directly
    run_script = Path(__file__).parent / "run.py"
    cmd = [
        sys.executable,
        str(run_script),
        task,
        "--session-dir",
        str(Path.home() / ".browser-agent" / "demo-session"),
    ]

    if headless:
        cmd.append("--headless")
    if auto_approve:
        cmd.append("--auto-approve")

    print(f"[bold cyan]Starting Browser Agent Demo[/bold cyan]")
    print(f"[dim]Task: {task}[/dim]")
    print(f"[dim]Headless: {headless}[/dim]")
    print(f"[dim]Auto-approve: {auto_approve}[/dim]")
    print()

    result = subprocess.run(cmd, check=False)
    return result.returncode


def main() -> None:
    """Main demo entry point."""
    parser = argparse.ArgumentParser(
        description="Browser Agent Demo - Autonomous AI browser controller"
    )
    parser.add_argument(
        "--task",
        type=str,
        default="Go to example.com and extract the page title",
        help="The task for the agent to perform (default: visit example.com and extract title)",
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

    args = parser.parse_args()

    # Run the demo
    exit_code = run_demo(
        task=args.task,
        headless=args.headless,
        auto_approve=args.auto_approve,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    # Display demo banner
    console.print(Panel.fit(
        "[bold cyan]Browser Agent Demo[/bold cyan]\n"
        "[dim]Autonomous AI browser controller demonstration[/dim]\n\n"
        "[yellow]Features demonstrated:[/yellow]\n"
        "  • Visible browser with persistent session\n"
        "  • Dynamic task planning\n"
        "  • Autonomous navigation and interaction\n"
        "  • Error recovery and stuck detection\n"
        "  • Destructive action confirmations\n"
        "  • Real-time progress display\n"
        "  • Completion report",
        title="Demo",
        border_style="cyan"
    ))

    console.print("\n[dim]The agent will perform a novel task (not pre-scripted).[/dim]")
    console.print("[dim]Watch as it plans, executes, and adapts to the page.[/dim]\n")

    main()

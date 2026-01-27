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
    launch_persistent_context,
)
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


def get_session_dir() -> Path:
    """Get the default session directory."""
    return Path.home() / ".browser-agent" / "session"


def display_step_progress(step_num: int, total_steps: int, action: str, details: str = "") -> None:
    """Display progress for the current step.

    Args:
        step_num: Current step number.
        total_steps: Total number of steps.
        action: Action being performed.
        details: Optional additional details.
    """
    progress_text = f"[bold cyan]Step {step_num}/{total_steps}:[/bold cyan] {action}"
    if details:
        progress_text += f"\n[dim]  {details}[/dim]"
    console.print(progress_text)


def display_confirmation_prompt(action: str, element_description: str) -> bool:
    """Display a confirmation prompt for destructive actions.

    Args:
        action: The action being performed.
        element_description: Description of the target element.

    Returns:
        True if user confirms, False otherwise.
    """
    console.print("\n")
    console.print(Panel(
        f"[bold red]DESTRUCTIVE ACTION[/bold red]\n"
        f"Action: {action}\n"
        f"Target: {element_description}\n\n"
        f"[yellow]This action may be irreversible.[/yellow]",
        title="⚠️  Confirmation Required",
        border_style="red"
    ))

    response = console.input("\n[bold yellow]Proceed? (yes/no):[/bold yellow] ").strip().lower()
    return response in ("yes", "y")


def display_completion_report(
    total_steps: int,
    successful_steps: int,
    failed_steps: int,
    final_message: str,
) -> None:
    """Display a completion report.

    Args:
        total_steps: Total number of steps executed.
        successful_steps: Number of successful steps.
        failed_steps: Number of failed steps.
        final_message: Final completion message.
    """
    console.print("\n")
    console.print(Panel(
        f"[bold green]Task Complete![/bold green]\n\n"
        f"Total steps: {total_steps}\n"
        f"Successful: [green]{successful_steps}[/green]\n"
        f"Failed: [red]{failed_steps}[/red]\n\n"
        f"[dim]{final_message}[/dim]",
        title="Summary"
    ))


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
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve all actions without confirmation (use with caution)",
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
    if args.auto_approve:
        console.print("[yellow][dim]Auto-approve mode: ENABLED[/dim][/yellow]")

    # Launch browser
    with sync_playwright() as p:
        try:
            console.print("\n[yellow]Launching browser...[/yellow]")
            with console.status("[bold green]Starting browser...", spinner="dots"):
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
            safety_agent = SafetyAgent()

            # Create planner and navigator
            planner = PlannerAgent()
            navigator = NavigatorAgent(page, registry)

            # Generate plan
            console.print("\n[yellow]Creating execution plan...[/yellow]")
            plan = planner.create_plan(task)
            console.print(f"[green]Plan created with {len(plan)} steps[/green]")

            # Display plan summary
            table = Table(title="Execution Plan", show_header=True, header_style="bold cyan")
            table.add_column("#", style="dim", width=3)
            table.add_column("Step", style="cyan")
            for i, step in enumerate(plan, 1):
                table.add_row(str(i), step)
            console.print(table)

            # Execute plan with progress display
            successful_steps = 0
            failed_steps = 0

            for step_num, step_description in enumerate(plan, 1):
                display_step_progress(
                    step_num,
                    len(plan),
                    f"Executing: {step_description[:60]}..."
                )

                # Check for destructive actions
                is_destructive = any(
                    pattern in step_description.lower()
                    for pattern in ["delete", "remove", "spam", "submit", "payment", "checkout"]
                )

                if is_destructive and not args.auto_approve:
                    confirmed = display_confirmation_prompt(
                        step_description.split()[0] if step_description.split() else "action",
                        step_description
                    )
                    if not confirmed:
                        console.print("[yellow]Action skipped by user.[/yellow]")
                        failed_steps += 1
                        continue

                # Execute the step
                result = navigator.execute_step(step_description)

                if result.success:
                    successful_steps += 1
                    console.print(f"[green]✓[/green] {result.message}")
                else:
                    failed_steps += 1
                    console.print(f"[red]✗[/red] {result.message}")
                    if result.error:
                        console.print(f"[dim]Error: {result.error}[/dim]")

                # Check if stuck
                context_tracker.record_action(
                    action_type=step_description.split()[0] if step_description.split() else "unknown",
                    success=result.success,
                )
                # TODO: stuck detection will be replaced by SDK ReAct loop (US-011)

            # Display completion report
            display_completion_report(
                total_steps=len(plan),
                successful_steps=successful_steps,
                failed_steps=failed_steps,
                final_message=f"Task '{task}' completed with {failed_steps} error(s)." if failed_steps == 0 else f"Task '{task}' completed with {failed_steps} error(s).",
            )

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
            console.print(f"\n[red]Error: {e}[/red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            return


if __name__ == "__main__":
    main()

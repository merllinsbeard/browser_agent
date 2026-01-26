#!/usr/bin/env python3
"""Evaluation script for browser-agent."""

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
from rich.table import Table

console = Console()


@dataclass
class TaskResult:
    """Result of running a single test task."""

    task_name: str
    task_description: str
    success: bool
    steps_executed: int
    steps_succeeded: int
    steps_failed: int
    user_inputs_required: int = 0
    was_stuck: bool = False
    error_message: str = ""
    duration_seconds: float = 0.0


@dataclass
class EvaluationMetrics:
    """Aggregated metrics from evaluation runs."""

    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_steps: int = 0
    total_successful_steps: int = 0
    total_failed_steps: int = 0
    total_user_inputs: int = 0
    total_stuck_situations: int = 0
    total_duration: float = 0.0

    def get_success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.successful_tasks / self.total_tasks) * 100

    def get_avg_steps(self) -> float:
        """Calculate average steps per task."""
        if self.total_tasks == 0:
            return 0.0
        return self.total_steps / self.total_tasks

    def get_avg_user_inputs(self) -> float:
        """Calculate average user inputs per task."""
        if self.total_tasks == 0:
            return 0.0
        return self.total_user_inputs / self.total_tasks


# Predefined test tasks for evaluation
TEST_TASKS = [
    {
        "name": "Simple Navigation",
        "description": "Navigate to https://example.com",
        "expected_steps": 1,
        "requires_user_input": False,
    },
    {
        "name": "Search Query",
        "description": "Go to Google and search for 'python tutorial'",
        "expected_steps": 3,
        "requires_user_input": False,
    },
    {
        "name": "Form Fill",
        "description": "Navigate to a form and fill in sample data",
        "description_detailed": "Go to https://www.w3schools.com/html/html_forms.asp and identify the form elements",
        "expected_steps": 2,
        "requires_user_input": False,
    },
]


def run_single_task(
    task: dict[str, Any],
    session_dir: Path,
    headless: bool = True,
) -> TaskResult:
    """Run a single test task and collect metrics.

    Args:
        task: Task dictionary with name, description, etc.
        session_dir: Directory for browser session.
        headless: Whether to run in headless mode.

    Returns:
        TaskResult with metrics.
    """
    import time

    task_name = task.get("name", "Unknown")
    task_description = task.get("description", task.get("description_detailed", task.get("name", "")))

    start_time = time.time()

    try:
        with sync_playwright() as p:
            context = launch_persistent_context(
                p,
                user_data_dir=session_dir,
                headless=headless,
            )

            pages = context.pages
            if pages:
                page = pages[0]
            else:
                page = context.new_page()

            # Initialize agent components
            registry = ElementRegistry()
            context_tracker = ContextTracker()
            stuck_detector = StuckDetector()

            planner = PlannerAgent()
            navigator = NavigatorAgent(page, registry, console)

            # Create plan
            plan = planner.create_plan(task_description)

            # Track if user input was required (destructive actions)
            user_inputs_required = 0
            for step in plan:
                if any(pattern in step.lower() for pattern in ["delete", "remove", "submit", "payment"]):
                    user_inputs_required += 1

            # Execute plan
            steps_succeeded = 0
            steps_failed = 0

            for step_description in plan:
                result = navigator.execute_step(step_description)

                if result.success:
                    steps_succeeded += 1
                else:
                    steps_failed += 1

                context_tracker.record_action(
                    action_type=step_description.split()[0] if step_description.split() else "unknown",
                    success=result.success,
                )

                stuck_detector.record_action(
                    result,
                    current_url=page.url if hasattr(page, "url") else "",
                )

            duration = time.time() - start_time

            context.close()

            return TaskResult(
                task_name=task_name,
                task_description=task_description,
                success=steps_failed == 0,
                steps_executed=len(plan),
                steps_succeeded=steps_succeeded,
                steps_failed=steps_failed,
                user_inputs_required=user_inputs_required,
                was_stuck=stuck_detector.is_stuck(),
                duration_seconds=duration,
            )

    except Exception as e:
        duration = time.time() - start_time
        return TaskResult(
            task_name=task_name,
            task_description=task_description,
            success=False,
            steps_executed=0,
            steps_succeeded=0,
            steps_failed=0,
            error_message=str(e),
            duration_seconds=duration,
        )


def run_evaluation(
    tasks: list[dict[str, Any]] | None = None,
    headless: bool = True,
) -> EvaluationMetrics:
    """Run evaluation on test tasks.

    Args:
        tasks: List of test tasks. If None, uses default TEST_TASKS.
        headless: Whether to run in headless mode.

    Returns:
        EvaluationMetrics with aggregated results.
    """
    if tasks is None:
        tasks = TEST_TASKS

    results: list[TaskResult] = []
    session_dir = Path.home() / ".browser-agent" / "eval-session"
    session_dir.mkdir(parents=True, exist_ok=True)

    with console.status("[bold green]Running evaluation...", spinner="dots"):
        for i, task in enumerate(tasks, 1):
            console.print(f"\n[yellow]Task {i}/{len(tasks)}:[/yellow] {task.get('name', 'Unknown')}")
            result = run_single_task(task, session_dir, headless)
            results.append(result)

            if result.success:
                console.print(f"[green]✓[/green] Success ({result.steps_executed} steps, {result.duration_seconds:.1f}s)")
            else:
                console.print(f"[red]✗[/red] Failed ({result.error_message or 'Unknown error'})")

    # Aggregate metrics
    metrics = EvaluationMetrics()
    for result in results:
        metrics.total_tasks += 1
        if result.success:
            metrics.successful_tasks += 1
        else:
            metrics.failed_tasks += 1
        metrics.total_steps += result.steps_executed
        metrics.total_successful_steps += result.steps_succeeded
        metrics.total_failed_steps += result.steps_failed
        metrics.total_user_inputs += result.user_inputs_required
        if result.was_stuck:
            metrics.total_stuck_situations += 1
        metrics.total_duration += result.duration_seconds

    return metrics


def display_metrics(metrics: EvaluationMetrics) -> None:
    """Display evaluation metrics in a formatted table.

    Args:
        metrics: The metrics to display.
    """
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Evaluation Report[/bold cyan]",
        border_style="cyan"
    ))

    # Summary table
    table = Table(title="Overall Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    success_rate = metrics.get_success_rate()
    success_rate_style = "green" if success_rate >= 80 else "yellow" if success_rate >= 50 else "red"

    table.add_row("Total Tasks", str(metrics.total_tasks))
    table.add_row("Success Rate", f"[{success_rate_style}]{success_rate:.1f}%[/{success_rate_style}]")
    table.add_row("Successful Tasks", f"[green]{metrics.successful_tasks}[/green]")
    table.add_row("Failed Tasks", f"[red]{metrics.failed_tasks}[/red]")
    table.add_row("", "")  # spacer
    table.add_row("Avg Steps/Task", f"{metrics.get_avg_steps():.1f}")
    table.add_row("Total Steps", str(metrics.total_steps))
    table.add_row("Successful Steps", f"[green]{metrics.total_successful_steps}[/green]")
    table.add_row("Failed Steps", f"[red]{metrics.total_failed_steps}[/red]")
    table.add_row("", "")  # spacer
    table.add_row("Avg User Inputs/Task", f"{metrics.get_avg_user_inputs():.1f}")
    table.add_row("Total User Inputs", str(metrics.total_user_inputs))
    table.add_row("Stuck Situations", f"[yellow]{metrics.total_stuck_situations}[/yellow]")
    table.add_row("", "")  # spacer
    table.add_row("Total Duration", f"{metrics.total_duration:.1f}s")
    table.add_row("Avg Duration/Task", f"{metrics.total_duration / metrics.total_tasks if metrics.total_tasks > 0 else 0:.1f}s")

    console.print(table)


def main() -> None:
    """Run evaluation tests."""
    parser = argparse.ArgumentParser(
        description="Browser Agent Evaluation Suite"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run in headless mode (default: True)",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run in visible mode (overrides --headless)",
    )
    parser.add_argument(
        "--tasks",
        type=int,
        default=None,
        help="Number of tasks to run (default: all)",
    )

    args = parser.parse_args()

    headless = args.headless and not args.visible

    # Display welcome
    console.print(Panel.fit(
        "[bold cyan]Browser Agent Evaluation[/bold cyan]\n"
        "[dim]Automated testing and metrics collection[/dim]",
        title="Evaluation Suite"
    ))

    # Select tasks
    tasks_to_run = TEST_TASKS
    if args.tasks is not None:
        tasks_to_run = TEST_TASKS[:args.tasks]

    console.print(f"\n[dim]Running {len(tasks_to_run)} task(s) in {'headless' if headless else 'visible'} mode...[/dim]")

    # Run evaluation
    metrics = run_evaluation(tasks_to_run, headless)

    # Display results
    display_metrics(metrics)


if __name__ == "__main__":
    main()

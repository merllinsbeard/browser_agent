#!/usr/bin/env python3
"""Evaluation script for browser-agent.

TODO: Rewrite using async architecture and Runner.run() (US-013).
The old eval logic used PlannerAgent/NavigatorAgent classes that have been
replaced by the OpenAI Agents SDK ReAct loop.
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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


# Predefined test tasks for evaluation
TEST_TASKS: list[dict[str, Any]] = [
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
        "expected_steps": 2,
        "requires_user_input": False,
    },
]


def display_metrics(metrics: EvaluationMetrics) -> None:
    """Display evaluation metrics in a formatted table."""
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]Evaluation Report[/bold cyan]",
        border_style="cyan"
    ))

    table = Table(title="Overall Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    success_rate = metrics.get_success_rate()
    success_rate_style = "green" if success_rate >= 80 else "yellow" if success_rate >= 50 else "red"

    table.add_row("Total Tasks", str(metrics.total_tasks))
    table.add_row("Success Rate", f"[{success_rate_style}]{success_rate:.1f}%[/{success_rate_style}]")
    table.add_row("Successful Tasks", f"[green]{metrics.successful_tasks}[/green]")
    table.add_row("Failed Tasks", f"[red]{metrics.failed_tasks}[/red]")

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

    console.print(Panel.fit(
        "[bold cyan]Browser Agent Evaluation[/bold cyan]\n"
        "[dim]Automated testing and metrics collection[/dim]",
        title="Evaluation Suite"
    ))

    console.print("\n[yellow]Evaluation script needs to be rewritten for the new SDK architecture.[/yellow]")
    console.print("[dim]See US-013 for the async rewrite using Runner.run().[/dim]")


if __name__ == "__main__":
    main()

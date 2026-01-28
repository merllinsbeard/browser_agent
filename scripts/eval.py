#!/usr/bin/env python3
"""Evaluation script for browser-agent using OpenAI Agents SDK.

Runs predefined test tasks through the Planner -> Navigator agent pipeline
and collects success/failure metrics.

Usage:
    uv run python scripts/eval.py [--headless] [--visible] [--tasks N]
"""

import argparse
import asyncio
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
from rich.table import Table

console = Console()

EVAL_SESSION_DIR = Path.home() / ".browser-agent" / "eval-session"


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
    table.add_row("Total Duration", f"{metrics.total_duration:.1f}s")

    console.print(table)


async def run_evaluation(
    headless: bool = True,
    max_tasks: int | None = None,
) -> None:
    """Run evaluation tasks through the agent pipeline.

    Args:
        headless: Whether to run in headless mode.
        max_tasks: Maximum number of tasks to run (None = all).
    """
    tasks = TEST_TASKS[:max_tasks] if max_tasks else TEST_TASKS
    results: list[TaskResult] = []

    # Configure SDK LLM client
    try:
        model_provider = setup_openrouter_for_sdk()
    except Exception as e:
        console.print(f"\n[red]LLM setup failed: {e}[/red]")
        console.print("[dim]Ensure OPENROUTER_API_KEY is set.[/dim]")
        return

    # Launch browser
    try:
        pw = await async_playwright().start()
    except Exception as e:
        console.print(f"\n[red]Playwright failed to start: {e}[/red]")
        console.print("[dim]Try: playwright install chromium[/dim]")
        return

    context = None
    try:
        # Clean eval session
        if EVAL_SESSION_DIR.exists():
            shutil.rmtree(EVAL_SESSION_DIR)
        EVAL_SESSION_DIR.mkdir(parents=True, exist_ok=True)

        context = await launch_persistent_context_async(
            pw,
            user_data_dir=EVAL_SESSION_DIR,
            headless=headless,
        )

        pages = context.pages
        page = pages[0] if pages else await context.new_page()

        logEvent("eval_start", {"total_tasks": len(tasks), "headless": headless})

        for i, task_def in enumerate(tasks):
            task_name = task_def["name"]
            task_desc = task_def["description"]

            console.print(f"\n[bold yellow]Task {i + 1}/{len(tasks)}:[/bold yellow] {task_name}")
            console.print(f"[dim]{task_desc}[/dim]")

            # Fresh registry and tools for each task
            registry = ElementRegistry()
            tools = create_browser_tools(page, registry, auto_approve=True)

            navigator = create_navigator_agent(tools)
            planner = create_planner_agent(navigator)

            start_time = time.monotonic()
            try:
                run_config = RunConfig(model_provider=model_provider)
                result = await Runner.run(planner, task_desc, max_turns=15, run_config=run_config)
                duration = time.monotonic() - start_time

                results.append(TaskResult(
                    task_name=task_name,
                    task_description=task_desc,
                    success=True,
                    steps_executed=1,
                    steps_succeeded=1,
                    steps_failed=0,
                    duration_seconds=duration,
                ))
                console.print(f"  [green]PASS[/green] ({duration:.1f}s) — {str(result.final_output)[:100]}")

            except MaxTurnsExceeded:
                duration = time.monotonic() - start_time
                results.append(TaskResult(
                    task_name=task_name,
                    task_description=task_desc,
                    success=False,
                    steps_executed=15,
                    steps_succeeded=0,
                    steps_failed=1,
                    error_message="Max turns exceeded (15)",
                    duration_seconds=duration,
                ))
                console.print(f"  [red]FAIL[/red] ({duration:.1f}s) — Max turns exceeded")

            except Exception as e:
                duration = time.monotonic() - start_time
                logError(ErrorIds.UNEXPECTED_ERROR, f"Eval task failed: {e}", exc_info=True)
                results.append(TaskResult(
                    task_name=task_name,
                    task_description=task_desc,
                    success=False,
                    steps_executed=0,
                    steps_succeeded=0,
                    steps_failed=1,
                    error_message=str(e),
                    duration_seconds=duration,
                ))
                console.print(f"  [red]FAIL[/red] ({duration:.1f}s) — {e}")

        # Aggregate metrics
        metrics = EvaluationMetrics(
            total_tasks=len(results),
            successful_tasks=sum(1 for r in results if r.success),
            failed_tasks=sum(1 for r in results if not r.success),
            total_steps=sum(r.steps_executed for r in results),
            total_successful_steps=sum(r.steps_succeeded for r in results),
            total_failed_steps=sum(r.steps_failed for r in results),
            total_duration=sum(r.duration_seconds for r in results),
        )

        logEvent("eval_complete", {
            "success_rate": metrics.get_success_rate(),
            "total_tasks": metrics.total_tasks,
        })
        display_metrics(metrics)

    except Exception as e:
        logError(ErrorIds.UNEXPECTED_ERROR, f"Eval script error: {e}", exc_info=True)
        console.print(f"\n[red]Error: {e}[/red]")
    finally:
        if context is not None:
            await context.close()
        await pw.stop()


async def main() -> None:
    """Main eval entry point."""
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

    headless = not args.visible

    await run_evaluation(
        headless=headless,
        max_tasks=args.tasks,
    )


if __name__ == "__main__":
    asyncio.run(main())

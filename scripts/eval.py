#!/usr/bin/env python3
"""Evaluation script for browser-agent."""

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table

console = Console()


def main() -> None:
    """Run evaluation tests."""
    console.print("[bold cyan]Browser Agent Evaluation[/bold cyan]")

    # TODO: Implement full evaluation suite
    table = Table(title="Evaluation Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Success Rate", "N/A (not implemented)")
    table.add_row("Avg Steps", "N/A (not implemented)")
    table.add_row("User Inputs", "N/A (not implemented)")
    table.add_row("Stuck Situations", "N/A (not implemented)")

    console.print(table)
    console.print("\n[yellow]Evaluation suite in progress...[/yellow]")


if __name__ == "__main__":
    main()

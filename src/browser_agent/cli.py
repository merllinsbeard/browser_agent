"""CLI entry point for browser-agent."""

from rich.console import Console

console = Console()


def main() -> None:
    """Main CLI entry point."""
    console.print("[bold cyan]Browser Agent[/bold cyan] - Autonomous AI browser controller")
    console.print("Use [bold]scripts/run.py[/bold] to run the agent interactively")


if __name__ == "__main__":
    main()

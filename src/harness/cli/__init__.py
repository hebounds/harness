"""CLI entrypoint for the harness system."""

from __future__ import annotations

import typer

from harness.cli.commands.init import init
from harness.cli.commands.plan import plan
from harness.cli.commands.run import run
from harness.cli.commands.status import status

app = typer.Typer(
    name="harness",
    help="An opinionated agent orchestration system.",
    no_args_is_help=True,
)

app.command()(init)
app.command()(run)
app.command()(plan)
app.command()(status)


def main() -> None:
    """Entry point."""
    app()


if __name__ == "__main__":
    main()

"""harness init command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from harness.cli._utils import console
from harness.config import DEFAULT_CONFIG_TEMPLATE


def init(
    path: Annotated[
        Path,
        typer.Option("--path", "-p", help="Path to create config file"),
    ] = Path("harness_config.py"),
) -> None:
    """Scaffold a harness_config.py with sensible defaults."""
    if path.exists():
        overwrite = typer.confirm(f"{path} already exists. Overwrite?")
        if not overwrite:
            raise typer.Abort()

    path.write_text(DEFAULT_CONFIG_TEMPLATE)
    console.print(f"[green]Created config:[/green] {path}")

    for dir_name in ["progress", "tasks/claims", ".harness"]:
        dir_path = Path(dir_name)
        dir_path.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]Created directory:[/green] {dir_path}")

"""harness status command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from harness.cli._utils import console, load_config, load_prd
from harness.core.models.prd import StoryStatus


def status(
    config_path: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to harness config"),
    ] = Path("harness_config.py"),
) -> None:
    """Show the status of all stories in the active PRD."""
    cfg = load_config(config_path)
    prd = load_prd(cfg.prd_path)

    table = Table(title=f"PRD Status: {prd.project}")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Status", style="green")
    table.add_column("Depends On", style="dim")

    for story in prd.user_stories:
        status_str = "✓ passed" if story.passes else story.status.value
        style = "green" if story.passes else ("red" if story.status == StoryStatus.FAILED else "")
        deps = ", ".join(story.depends_on) if story.depends_on else "—"
        table.add_row(story.id, story.title, f"[{style}]{status_str}[/{style}]", deps)

    console.print(table)

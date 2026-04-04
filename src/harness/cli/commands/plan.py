"""harness plan command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.table import Table

from harness.cli._utils import console, load_config, load_prd


def plan(
    config_path: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to harness config"),
    ] = Path("harness_config.py"),
) -> None:
    """Print the execution plan: parallel groups, critical path, waves."""
    cfg = load_config(config_path)
    prd = load_prd(cfg.prd_path)

    from harness.core.scheduler import DagScheduler

    scheduler = DagScheduler(prd)
    schedule = scheduler.plan()

    table = Table(title=f"Execution Plan: {prd.project}")
    table.add_column("Wave", style="cyan")
    table.add_column("Stories", style="green")
    table.add_column("Parallel", style="yellow")

    for i, wave in enumerate(schedule.waves, 1):
        ids = ", ".join(s.id for s in wave)
        table.add_row(str(i), ids, str(len(wave)))

    console.print(table)
    console.print(f"\nCritical path: {' → '.join(schedule.critical_path)}")
    console.print(f"Total waves: {len(schedule.waves)}")

"""harness run command."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated, Optional

import typer

from harness.cli._utils import console, load_config, load_prd, setup_logging


def run(
    config_path: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to harness config"),
    ] = Path("harness_config.py"),
    workflow: Annotated[
        Optional[str],
        typer.Option("--workflow", "-w", help="Named workflow to execute"),
    ] = None,
    parallel: Annotated[
        Optional[int],
        typer.Option("--parallel", help="Max parallel agents"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be done without executing"),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug logging"),
    ] = False,
) -> None:
    """Run the harness agent loop."""
    setup_logging(verbose)
    cfg = load_config(config_path)

    if parallel is not None:
        cfg.max_parallel_agents = parallel

    prd = load_prd(cfg.prd_path)
    completed = {s.id for s in prd.user_stories if s.passes}
    ready = prd.ready_stories(completed)

    if not ready:
        console.print("[yellow]No stories ready for execution.[/yellow]")
        if all(s.passes for s in prd.user_stories):
            console.print("[green]All stories completed![/green]")
        else:
            console.print("[yellow]Remaining stories have unmet dependencies or are failed.[/yellow]")
        raise typer.Exit(0)

    if dry_run:
        console.print("[bold]Dry run — would execute:[/bold]")
        for story in ready:
            console.print(f"  • {story.id}: {story.title}")
        raise typer.Exit(0)

    # Import here to avoid circular imports and heavy deps at CLI parse time
    from harness.core.orchestrator import Orchestrator

    orchestrator = Orchestrator(config=cfg, prd=prd)

    try:
        asyncio.run(orchestrator.run(ready))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted — releasing claims...[/yellow]")
        asyncio.run(orchestrator.cleanup())
        raise typer.Exit(1)

"""Shared CLI utilities: console, logging, loaders."""

from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.logging import RichHandler

from harness.config import HarnessConfig
from harness.core.models.prd import Prd

console = Console()
logger = logging.getLogger("harness")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def load_config(config_path: Path) -> HarnessConfig:
    """Load HarnessConfig from a Python config file."""
    if not config_path.exists():
        console.print(f"[red]Config file not found:[/red] {config_path}")
        console.print("Run [bold]harness init[/bold] to create one.")
        raise typer.Exit(1)

    spec = importlib.util.spec_from_file_location("harness_config", config_path)
    if spec is None or spec.loader is None:
        console.print(f"[red]Cannot load config:[/red] {config_path}")
        raise typer.Exit(1)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    config_obj = getattr(module, "config", None)
    if not isinstance(config_obj, HarnessConfig):
        console.print(
            "[red]Config file must export a 'config' variable of type HarnessConfig[/red]"
        )
        raise typer.Exit(1)

    return config_obj


def load_prd(prd_path: Path) -> Prd:
    """Load and validate a PRD from JSON."""
    if not prd_path.exists():
        console.print(f"[red]PRD file not found:[/red] {prd_path}")
        raise typer.Exit(1)

    data = json.loads(prd_path.read_text())
    return Prd.model_validate(data)

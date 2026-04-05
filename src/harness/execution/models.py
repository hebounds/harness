"""Data models for the execution layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Context:
    root_path: Path
    worktree_path: Path
    branch_name: str
    story_id: str

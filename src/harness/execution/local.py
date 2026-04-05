"""LocalWorktreeEnvironment — executes commands in a local filesystem worktree."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Literal

from harness.core.models.prd import Story
from harness.execution.models import Context


class LocalWorktreeEnvironment:
    """ExecutionEnvironment that runs directly on the local filesystem."""

    network_policy: Literal["full", "restricted", "gapped"] = "full"

    def __init__(self, root_path: Path) -> None:
        self._root_path = root_path
        self._context: Context | None = None

    def get_root(self) -> Path:
        return self._root_path

    async def setup(self, story: Story) -> Context:
        worktree_path = self._root_path / ".harness" / "worktrees" / story.id
        branch_name = f"worktree-{story.id.lower()}"
        self._context = Context(
            root_path=self._root_path,
            worktree_path=worktree_path,
            branch_name=branch_name,
            story_id=story.id,
        )
        return self._context

    async def execute(self, command: str, *args: str) -> tuple[int, str, str]:
        cwd = (
            str(self._context.worktree_path)
            if self._context is not None
            else str(self._root_path)
        )
        proc = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        return (
            proc.returncode if proc.returncode is not None else 1,
            stdout_bytes.decode(),
            stderr_bytes.decode(),
        )

    async def teardown(self) -> None:
        self._context = None

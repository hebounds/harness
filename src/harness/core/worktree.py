"""WorktreeManager — git worktree lifecycle management."""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.execution.base import ExecutionEnvironment

__all__ = ["WorktreeManager"]


class WorktreeManager:
    """Manages git worktree creation and teardown for story isolation.

    Each story runs in an isolated git worktree located at
    ``{root_path}/.harness/worktrees/{story_id}/``.
    """

    def __init__(
        self,
        root_path: Path,
        env: ExecutionEnvironment,
        dep_install_command: list[str] | None = None,
    ) -> None:
        self._root_path = root_path
        self._env = env
        self._dep_install_command = dep_install_command

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _worktree_path(self, story_id: str) -> Path:
        return self._root_path / ".harness" / "worktrees" / story_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_path(self, story_id: str) -> Path | None:
        """Return the worktree path for *story_id* if it exists, else None."""
        path = self._worktree_path(story_id)
        return path if path.is_dir() else None

    async def create(self, story_id: str, branch_name: str) -> Path:
        """Create a git worktree for *story_id* on a new branch *branch_name*.

        Steps:
        1. ``git worktree add -b <branch_name> <worktree_path>`` from repo root
        2. Symlink ``.env`` from repo root into the worktree if present
        3. Run dep-install command inside the worktree if configured
        """
        worktree_path = self._worktree_path(story_id)
        worktree_path.parent.mkdir(parents=True, exist_ok=True)

        returncode, _stdout, stderr = await self._env.execute(
            "git",
            "worktree",
            "add",
            "-b",
            branch_name,
            str(worktree_path),
        )
        if returncode != 0:
            raise RuntimeError(
                f"git worktree add failed for story {story_id!r}: {stderr.strip()}"
            )

        # Symlink .env from the repo root into the worktree if it exists
        env_source = self._root_path / ".env"
        if env_source.exists():
            env_link = worktree_path / ".env"
            if not env_link.exists():
                env_link.symlink_to(env_source)

        # Run dep-install inside the worktree
        if self._dep_install_command:
            cmd, *args = self._dep_install_command
            proc = await asyncio.create_subprocess_exec(
                cmd,
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=worktree_path,
            )
            _, stderr_bytes = await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError(
                    f"dep-install failed for story {story_id!r}: {stderr_bytes.decode().strip()}"
                )

        return worktree_path

    async def teardown(self, story_id: str) -> None:
        """Remove the worktree for *story_id* via ``git worktree remove --force``."""
        worktree_path = self._worktree_path(story_id)

        returncode, _stdout, _stderr = await self._env.execute(
            "git",
            "worktree",
            "remove",
            "--force",
            str(worktree_path),
        )
        if returncode != 0:
            # Best-effort cleanup: remove directory and prune stale refs
            if worktree_path.is_dir():
                shutil.rmtree(worktree_path)
            await self._env.execute("git", "worktree", "prune")

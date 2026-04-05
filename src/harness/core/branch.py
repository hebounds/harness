"""BranchManager — git branch creation and merging."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.execution.base import ExecutionEnvironment

__all__ = ["BranchManager"]

_log = logging.getLogger(__name__)


class BranchManager:
    """Manages git branch creation and merging.

    All git operations are delegated to the provided
    :class:`~harness.execution.base.ExecutionEnvironment`.
    """

    def __init__(self, root_path: Path, env: ExecutionEnvironment) -> None:
        self._root_path = root_path
        self._env = env

    async def create(self, branch_name: str, base_branch: str) -> None:
        """Create *branch_name* from *base_branch*.

        Raises :class:`RuntimeError` if the git command fails.
        """
        returncode, _stdout, stderr = await self._env.execute(
            "git",
            "checkout",
            "-b",
            branch_name,
            base_branch,
        )
        if returncode != 0:
            raise RuntimeError(
                f"git checkout -b {branch_name!r} {base_branch!r} failed: {stderr.strip()}"
            )

    async def merge(self, branch_name: str, base_branch: str) -> bool:
        """Merge *branch_name* into *base_branch*.

        Returns ``True`` on a clean merge, ``False`` when merge conflicts are
        detected.  Does **not** raise on conflicts — the caller is responsible
        for logging and pausing for human intervention.
        """
        # Checkout the base branch first
        returncode, _stdout, stderr = await self._env.execute(
            "git",
            "checkout",
            base_branch,
        )
        if returncode != 0:
            raise RuntimeError(
                f"git checkout {base_branch!r} failed: {stderr.strip()}"
            )

        returncode, _stdout, stderr = await self._env.execute(
            "git",
            "merge",
            "--no-ff",
            branch_name,
        )
        if returncode != 0:
            _log.warning(
                "Merge conflict detected when merging %r into %r — "
                "human intervention required. git output: %s",
                branch_name,
                base_branch,
                stderr.strip(),
            )
            return False

        return True

    async def has_conflicts(self, branch_name: str) -> bool:
        """Return ``True`` if merging *branch_name* into HEAD would produce conflicts.

        Uses ``git merge --no-commit --no-ff`` followed by ``git merge --abort``
        so the working tree is left clean regardless of the result.
        """
        returncode, _stdout, _stderr = await self._env.execute(
            "git",
            "merge",
            "--no-commit",
            "--no-ff",
            branch_name,
        )
        if returncode != 0:
            # Conflict — abort and report
            await self._env.execute("git", "merge", "--abort")
            return True

        # Clean merge — reset to avoid a real merge commit
        await self._env.execute("git", "merge", "--abort")
        return False

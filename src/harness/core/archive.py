"""ArchiveManager — PRD and progress file archiving."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.execution.base import ExecutionEnvironment

__all__ = ["ArchiveManager"]


class ArchiveManager:
    """Archives PRD JSON and progress files into a date-stamped directory.

    The archive directory structure is::

        {archive_dir}/YYYY-MM-DD-{prd-name}/
            prd.json
            <progress_file>
    """

    def __init__(self, root_path: Path, env: ExecutionEnvironment) -> None:
        self._root_path = root_path
        self._env = env

    def archive(
        self,
        prd_path: Path,
        progress_path: Path,
        archive_dir: Path,
    ) -> Path:
        """Copy *prd_path* and *progress_path* into a new archive sub-directory.

        The sub-directory is named ``YYYY-MM-DD-{prd-stem}`` where *prd-stem*
        is the stem of *prd_path* (e.g. ``prd-agent-harness`` for
        ``prd-agent-harness.json``).

        Returns the :class:`~pathlib.Path` of the created archive directory.

        Raises :class:`FileNotFoundError` if either source file does not exist.
        """
        if not prd_path.exists():
            raise FileNotFoundError(f"PRD file not found: {prd_path}")
        if not progress_path.exists():
            raise FileNotFoundError(f"Progress file not found: {progress_path}")

        today = date.today().isoformat()  # YYYY-MM-DD
        prd_name = prd_path.stem  # strip extension
        dest_dir = archive_dir / f"{today}-{prd_name}"
        dest_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(prd_path, dest_dir / prd_path.name)
        shutil.copy2(progress_path, dest_dir / progress_path.name)

        return dest_dir

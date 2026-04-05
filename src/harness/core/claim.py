"""ClaimManager — atomic story claiming via O_CREAT | O_EXCL."""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path

__all__ = ["ClaimManager"]

_CLAIM_SUFFIX = ".claim"


class ClaimManager:
    """Atomic claim creation and release using filesystem O_CREAT|O_EXCL.

    Claim files are written to ``{root_path}/tasks/claims/{story_id}.claim``
    and contain an ISO-8601 timestamp and the PID of the claiming process.

    No global state — each instance is bound to a *root_path*.
    """

    def __init__(self, root_path: Path) -> None:
        self._claims_dir = root_path / "tasks" / "claims"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _claim_path(self, story_id: str) -> Path:
        return self._claims_dir / f"{story_id}{_CLAIM_SUFFIX}"

    def _ensure_claims_dir(self) -> None:
        self._claims_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def claim(self, story_id: str) -> bool:
        """Atomically create a claim file for *story_id*.

        Returns ``True`` when the claim was successfully created, ``False``
        if the story is already claimed by another process.  Never raises
        if the story is already claimed.
        """
        self._ensure_claims_dir()
        path = self._claim_path(story_id)
        timestamp = datetime.now(tz=timezone.utc).isoformat()
        pid = os.getpid()
        content = f"{timestamp}\n{pid}\n"
        try:
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            return False
        try:
            os.write(fd, content.encode())
        finally:
            os.close(fd)
        return True

    def release(self, story_id: str) -> None:
        """Delete the claim file for *story_id*.

        Safe to call when no claim exists.
        """
        path = self._claim_path(story_id)
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    def is_claimed(self, story_id: str) -> bool:
        """Return ``True`` if a claim file exists for *story_id*."""
        return self._claim_path(story_id).exists()

    def cleanup_stale(self, max_age_minutes: int = 30) -> list[str]:
        """Remove claim files older than *max_age_minutes* minutes.

        Returns the list of story IDs whose stale claims were removed.
        """
        if not self._claims_dir.exists():
            return []

        cutoff = time.time() - max_age_minutes * 60
        removed: list[str] = []

        for path in self._claims_dir.glob(f"*{_CLAIM_SUFFIX}"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed.append(path.stem)
            except FileNotFoundError:
                # Removed by a concurrent process — not an error.
                pass

        return removed

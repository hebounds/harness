"""ProgressManager — per-PRD progress tracking with token-aware summarization."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import tiktoken

from harness.core.models.progress import ProgressEntry

__all__ = ["ProgressManager"]

_log = logging.getLogger(__name__)
_ENCODING = tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_ENCODING.encode(text))


def _read_entries(path: Path) -> list[ProgressEntry]:
    """Read all ProgressEntry records from a JSON-lines file."""
    if not path.exists():
        return []
    entries: list[ProgressEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(ProgressEntry.model_validate_json(line))
    return entries


class ProgressManager:
    """Per-PRD progress tracking with token-aware summarization.

    Progress files live at ``{root_path}/tasks/progress/prd-{prd_name}.progress.json``
    (JSON lines — one ProgressEntry per line).  A shared codebase patterns file
    is kept at ``{root_path}/tasks/progress/codebase-patterns.md``.

    Parameters
    ----------
    root_path:
        Absolute path to the project root (no global state).
    prd_name:
        Identifier for the PRD, e.g. ``"agent-harness"``.
    """

    def __init__(self, root_path: Path, prd_name: str) -> None:
        self._progress_dir = root_path / "tasks" / "progress"
        self._prd_name = prd_name
        self._progress_file = self._progress_dir / f"prd-{prd_name}.progress.json"
        self._patterns_file = self._progress_dir / "codebase-patterns.md"

    def _ensure_progress_dir(self) -> None:
        self._progress_dir.mkdir(parents=True, exist_ok=True)

    def append(self, entry: ProgressEntry) -> None:
        """Append *entry* as a JSON line to the current PRD's progress file."""
        self._ensure_progress_dir()
        with self._progress_file.open("a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

    def get_entries(self, story_id: str | None = None) -> list[ProgressEntry]:
        """Return all entries, optionally filtered by *story_id*."""
        entries = _read_entries(self._progress_file)
        if story_id is not None:
            entries = [e for e in entries if e.story_id == story_id]
        return entries

    def summarize(self, max_tokens: int) -> str:
        """Fit the most recent entries and global patterns within *max_tokens*.

        Returns a compact JSON string of the entries that fit, prefixed by
        patterns when present.
        """
        patterns = (
            self._patterns_file.read_text(encoding="utf-8").strip()
            if self._patterns_file.exists()
            else ""
        )
        patterns_block = f"## Codebase Patterns\n\n{patterns}" if patterns else ""
        patterns_tokens = _count_tokens(patterns_block)

        if patterns_tokens >= max_tokens:
            tokens = _ENCODING.encode(patterns_block)
            return _ENCODING.decode(tokens[:max_tokens])

        remaining = max_tokens - patterns_tokens
        entries = list(reversed(self.get_entries()))  # newest first
        selected: list[ProgressEntry] = []
        used = 0
        for entry in entries:
            cost = _count_tokens(entry.model_dump_json())
            if used + cost > remaining:
                break
            selected.append(entry)
            used += cost

        output_parts: list[str] = []
        if patterns_block:
            output_parts.append(patterns_block)
        if selected:
            payload = json.dumps(
                [json.loads(e.model_dump_json()) for e in reversed(selected)],
                indent=2,
            )
            output_parts.append(f"## Recent Progress\n\n{payload}")
        return "\n\n".join(output_parts)

    def select_context(self, current_story_id: str, changed_files: list[str]) -> str:
        """Return focused context for *current_story_id*.

        Combines:
        1. Global codebase patterns
        2. All entries from the current PRD's progress file
        3. Entries from other PRDs whose ``files_changed`` overlap *changed_files*
        """
        changed_set = set(changed_files)
        output_parts: list[str] = []

        # 1. Global patterns
        if self._patterns_file.exists():
            patterns = self._patterns_file.read_text(encoding="utf-8").strip()
            if patterns:
                output_parts.append(f"## Codebase Patterns\n\n{patterns}")

        # 2. Current PRD entries
        current_entries = self.get_entries()
        if current_entries:
            payload = json.dumps(
                [json.loads(e.model_dump_json()) for e in current_entries], indent=2
            )
            output_parts.append(f"## Progress: {self._prd_name}\n\n{payload}")

        # 3. Cross-PRD entries whose changed files overlap
        cross_entries: list[tuple[str, ProgressEntry]] = []
        for progress_file in sorted(self._progress_dir.glob("*.progress.json")):
            if progress_file == self._progress_file:
                continue
            prd_label = progress_file.stem
            for entry in _read_entries(progress_file):
                if changed_set & set(entry.files_changed):
                    cross_entries.append((prd_label, entry))

        if cross_entries:
            cross_payload = json.dumps(
                [
                    {"prd": label, **json.loads(e.model_dump_json())}
                    for label, e in cross_entries
                ],
                indent=2,
            )
            output_parts.append(f"## Related Progress (other PRDs)\n\n{cross_payload}")

        return "\n\n".join(output_parts)

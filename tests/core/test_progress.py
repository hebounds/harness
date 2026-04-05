"""Tests for ProgressManager."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from harness.core.models.progress import ProgressEntry
from harness.core.progress import ProgressManager, _read_entries


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(
    story_id: str = "US-001",
    status: str = "completed",
    files_changed: list[str] | None = None,
    summary: str = "did the thing",
    timestamp: datetime | None = None,
) -> ProgressEntry:
    kwargs: dict = dict(story_id=story_id, status=status, summary=summary)
    if files_changed is not None:
        kwargs["files_changed"] = files_changed
    if timestamp is not None:
        kwargs["timestamp"] = timestamp
    return ProgressEntry(**kwargs)


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def mgr(root: Path) -> ProgressManager:
    return ProgressManager(root, "agent-harness")


# ---------------------------------------------------------------------------
# _read_entries round-trip
# ---------------------------------------------------------------------------


class TestReadEntries:
    def test_round_trip(self, root: Path) -> None:
        path = root / "test.progress.json"
        e = _entry(story_id="US-003", status="partial", files_changed=["x.py"], summary="halfway")
        path.write_text(e.model_dump_json() + "\n")
        entries = _read_entries(path)
        assert len(entries) == 1
        assert entries[0].story_id == "US-003"
        assert entries[0].status == "partial"
        assert entries[0].files_changed == ["x.py"]

    def test_missing_file_returns_empty(self, root: Path) -> None:
        assert _read_entries(root / "no-such.progress.json") == []

    def test_multiple_lines(self, root: Path) -> None:
        path = root / "multi.progress.json"
        e1 = _entry(story_id="US-001")
        e2 = _entry(story_id="US-002")
        path.write_text(e1.model_dump_json() + "\n" + e2.model_dump_json() + "\n")
        entries = _read_entries(path)
        assert [e.story_id for e in entries] == ["US-001", "US-002"]


# ---------------------------------------------------------------------------
# ProgressManager.append / get_entries
# ---------------------------------------------------------------------------


class TestAppend:
    def test_creates_progress_file(self, root: Path, mgr: ProgressManager) -> None:
        mgr.append(_entry())
        assert (root / "tasks" / "progress" / "prd-agent-harness.progress.json").exists()

    def test_creates_tasks_progress_dir(self, root: Path, mgr: ProgressManager) -> None:
        mgr.append(_entry())
        assert (root / "tasks" / "progress").is_dir()

    def test_multiple_entries_appended(self, mgr: ProgressManager) -> None:
        mgr.append(_entry(story_id="US-001", summary="first"))
        mgr.append(_entry(story_id="US-002", summary="second"))
        entries = mgr.get_entries()
        assert len(entries) == 2

    def test_entry_content_preserved(self, mgr: ProgressManager) -> None:
        mgr.append(_entry(story_id="US-007", status="failed", summary="oops"))
        entries = mgr.get_entries()
        assert entries[0].story_id == "US-007"
        assert entries[0].status == "failed"


class TestGetEntries:
    def test_empty_when_no_file(self, mgr: ProgressManager) -> None:
        assert mgr.get_entries() == []

    def test_filter_by_story_id(self, mgr: ProgressManager) -> None:
        mgr.append(_entry(story_id="US-001"))
        mgr.append(_entry(story_id="US-002"))
        mgr.append(_entry(story_id="US-001"))
        result = mgr.get_entries(story_id="US-001")
        assert len(result) == 2
        assert all(e.story_id == "US-001" for e in result)

    def test_no_filter_returns_all(self, mgr: ProgressManager) -> None:
        mgr.append(_entry(story_id="US-001"))
        mgr.append(_entry(story_id="US-002"))
        assert len(mgr.get_entries()) == 2


# ---------------------------------------------------------------------------
# ProgressManager.summarize
# ---------------------------------------------------------------------------


class TestSummarize:
    def test_returns_string(self, mgr: ProgressManager) -> None:
        mgr.append(_entry())
        result = mgr.summarize(max_tokens=500)
        assert isinstance(result, str)

    def test_includes_recent_entries(self, mgr: ProgressManager) -> None:
        mgr.append(_entry(story_id="US-001", summary="some work done"))
        result = mgr.summarize(max_tokens=500)
        assert "US-001" in result

    def test_includes_patterns_when_present(self, root: Path, mgr: ProgressManager) -> None:
        patterns_file = root / "tasks" / "progress" / "codebase-patterns.md"
        patterns_file.parent.mkdir(parents=True, exist_ok=True)
        patterns_file.write_text("- Use dependency injection everywhere\n")
        result = mgr.summarize(max_tokens=500)
        assert "dependency injection" in result

    def test_respects_token_ceiling(self, mgr: ProgressManager) -> None:
        # Add many entries so the full output would exceed the ceiling
        for i in range(20):
            mgr.append(_entry(story_id=f"US-{i:03d}", summary="x" * 200))
        result = mgr.summarize(max_tokens=100)
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        assert len(enc.encode(result)) <= 100

    def test_empty_progress_returns_empty(self, mgr: ProgressManager) -> None:
        assert mgr.summarize(max_tokens=500) == ""


# ---------------------------------------------------------------------------
# ProgressManager.select_context
# ---------------------------------------------------------------------------


class TestSelectContext:
    def test_includes_current_prd_entries(self, mgr: ProgressManager) -> None:
        mgr.append(_entry(story_id="US-001", summary="implemented widget"))
        result = mgr.select_context("US-001", [])
        assert "US-001" in result

    def test_includes_patterns(self, root: Path, mgr: ProgressManager) -> None:
        patterns_file = root / "tasks" / "progress" / "codebase-patterns.md"
        patterns_file.parent.mkdir(parents=True, exist_ok=True)
        patterns_file.write_text("- Use pydantic models\n")
        result = mgr.select_context("US-001", [])
        assert "pydantic" in result

    def test_cross_prd_overlap_included(self, root: Path) -> None:
        mgr_a = ProgressManager(root, "prd-a")
        mgr_b = ProgressManager(root, "prd-b")
        mgr_a.append(_entry(story_id="US-001", files_changed=["shared.py"], summary="shared file work"))
        # Select context with prd-b, referencing the same file
        result = mgr_b.select_context("US-002", ["shared.py"])
        assert "shared file work" in result

    def test_cross_prd_no_overlap_excluded(self, root: Path) -> None:
        mgr_a = ProgressManager(root, "prd-a")
        mgr_b = ProgressManager(root, "prd-b")
        mgr_a.append(_entry(story_id="US-001", files_changed=["other.py"], summary="unrelated"))
        result = mgr_b.select_context("US-002", ["mine.py"])
        assert "unrelated" not in result

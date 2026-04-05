"""Tests for ProgressEntry Pydantic model."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from harness.core.models.progress import ProgressEntry


class TestProgressEntryDefaults:
    def test_story_id_and_status(self) -> None:
        entry = ProgressEntry(story_id="US-001", status="completed")
        assert entry.story_id == "US-001"
        assert entry.status == "completed"

    def test_default_files_changed(self) -> None:
        assert ProgressEntry(story_id="US-001", status="completed").files_changed == []

    def test_timestamp_auto_set(self) -> None:
        before = datetime.now()
        entry = ProgressEntry(story_id="US-001", status="completed")
        after = datetime.now()
        assert before <= entry.timestamp <= after


class TestProgressEntryCustomValues:
    def test_explicit_timestamp(self) -> None:
        ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        entry = ProgressEntry(story_id="US-001", status="failed", timestamp=ts)
        assert entry.timestamp == ts

    def test_files_changed(self) -> None:
        entry = ProgressEntry(story_id="US-002", status="partial", files_changed=["src/foo.py"])
        assert entry.files_changed == ["src/foo.py"]

    def test_summary(self) -> None:
        entry = ProgressEntry(story_id="US-001", status="completed", summary="Did the thing")
        assert entry.summary == "Did the thing"


class TestProgressEntrySerialization:
    def test_json_round_trip(self) -> None:
        entry = ProgressEntry(
            story_id="US-003",
            status="partial",
            files_changed=["a.py", "b.py"],
            summary="Partly done",
        )
        restored = ProgressEntry.model_validate_json(entry.model_dump_json())
        assert restored.story_id == entry.story_id
        assert restored.status == entry.status
        assert restored.files_changed == entry.files_changed

    def test_timestamp_serialises_as_iso8601(self) -> None:
        ts = datetime(2026, 4, 4, 10, 30, 0, tzinfo=UTC)
        entry = ProgressEntry(story_id="US-001", status="completed", timestamp=ts)
        data = json.loads(entry.model_dump_json())
        parsed = datetime.fromisoformat(data["timestamp"])
        assert (parsed.year, parsed.month, parsed.day) == (2026, 4, 4)

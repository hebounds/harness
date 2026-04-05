"""Tests for ClaimManager."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from harness.core.claim import ClaimManager


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def manager(root: Path) -> ClaimManager:
    return ClaimManager(root)


class TestClaimPath:
    def test_claim_file_under_tasks_claims(self, root: Path, manager: ClaimManager) -> None:
        manager.claim("US-001")
        assert (root / "tasks" / "claims" / "US-001.claim").exists()


class TestClaim:
    def test_first_claim_returns_true(self, manager: ClaimManager) -> None:
        assert manager.claim("US-001") is True

    def test_duplicate_claim_returns_false(self, manager: ClaimManager) -> None:
        manager.claim("US-001")
        assert manager.claim("US-001") is False

    def test_different_stories_claimed_independently(self, manager: ClaimManager) -> None:
        assert manager.claim("US-001") is True
        assert manager.claim("US-002") is True

    def test_claim_file_contains_timestamp_and_pid(self, root: Path, manager: ClaimManager) -> None:
        manager.claim("US-001")
        content = (root / "tasks" / "claims" / "US-001.claim").read_text()
        lines = content.splitlines()
        assert len(lines) == 2
        # First line should be ISO-8601 timestamp (ends with +00:00 or Z)
        assert "T" in lines[0]
        # Second line should be current PID
        assert lines[1] == str(os.getpid())

    def test_creates_claims_dir_automatically(self, root: Path, manager: ClaimManager) -> None:
        claims_dir = root / "tasks" / "claims"
        assert not claims_dir.exists()
        manager.claim("US-001")
        assert claims_dir.is_dir()


class TestRelease:
    def test_release_removes_claim_file(self, root: Path, manager: ClaimManager) -> None:
        manager.claim("US-001")
        manager.release("US-001")
        assert not (root / "tasks" / "claims" / "US-001.claim").exists()

    def test_release_without_claim_is_safe(self, manager: ClaimManager) -> None:
        manager.release("US-001")  # should not raise

    def test_release_allows_reclaim(self, manager: ClaimManager) -> None:
        manager.claim("US-001")
        manager.release("US-001")
        assert manager.claim("US-001") is True


class TestIsClaimed:
    def test_not_claimed_initially(self, manager: ClaimManager) -> None:
        assert manager.is_claimed("US-001") is False

    def test_claimed_after_claim(self, manager: ClaimManager) -> None:
        manager.claim("US-001")
        assert manager.is_claimed("US-001") is True

    def test_not_claimed_after_release(self, manager: ClaimManager) -> None:
        manager.claim("US-001")
        manager.release("US-001")
        assert manager.is_claimed("US-001") is False


class TestCleanupStale:
    def test_returns_empty_when_no_claims_dir(self, manager: ClaimManager) -> None:
        assert manager.cleanup_stale() == []

    def test_removes_old_claim_and_returns_id(self, root: Path, manager: ClaimManager) -> None:
        manager.claim("US-001")
        claim_path = root / "tasks" / "claims" / "US-001.claim"
        # Backdate the file modification time by 31 minutes
        old_time = time.time() - 31 * 60
        os.utime(claim_path, (old_time, old_time))
        removed = manager.cleanup_stale(max_age_minutes=30)
        assert removed == ["US-001"]
        assert not claim_path.exists()

    def test_keeps_fresh_claim(self, root: Path, manager: ClaimManager) -> None:
        manager.claim("US-001")
        removed = manager.cleanup_stale(max_age_minutes=30)
        assert removed == []
        assert (root / "tasks" / "claims" / "US-001.claim").exists()

    def test_removes_only_stale_claims(self, root: Path, manager: ClaimManager) -> None:
        manager.claim("US-001")
        manager.claim("US-002")
        stale_path = root / "tasks" / "claims" / "US-001.claim"
        old_time = time.time() - 31 * 60
        os.utime(stale_path, (old_time, old_time))
        removed = manager.cleanup_stale(max_age_minutes=30)
        assert removed == ["US-001"]
        assert not stale_path.exists()
        assert (root / "tasks" / "claims" / "US-002.claim").exists()

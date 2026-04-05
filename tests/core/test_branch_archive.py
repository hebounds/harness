"""Tests for BranchManager and ArchiveManager."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from typing import Literal

import pytest

from harness.core.archive import ArchiveManager
from harness.core.branch import BranchManager
from harness.core.models.prd import Story
from harness.execution.models import Context


# ---------------------------------------------------------------------------
# Minimal mock ExecutionEnvironment (mirrors test_worktree.py style)
# ---------------------------------------------------------------------------


class _MockEnv:
    network_policy: Literal["full", "restricted", "gapped"] = "full"

    def __init__(self, root_path: Path) -> None:
        self._root_path = root_path
        self.calls: list[tuple[str, ...]] = []
        self._responses: list[tuple[int, str, str]] = []

    def get_root(self) -> Path:
        return self._root_path

    def set_responses(self, responses: list[tuple[int, str, str]]) -> None:
        self._responses = list(responses)

    async def setup(self, story: Story) -> Context:  # pragma: no cover
        return Context(
            root_path=self._root_path,
            worktree_path=self._root_path,
            branch_name="",
            story_id=story.id,
        )

    async def execute(self, command: str, *args: str) -> tuple[int, str, str]:
        self.calls.append((command, *args))
        if self._responses:
            return self._responses.pop(0)
        return (0, "", "")

    async def teardown(self) -> None:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture()
def env(root: Path) -> _MockEnv:
    return _MockEnv(root)


@pytest.fixture()
def branch_mgr(root: Path, env: _MockEnv) -> BranchManager:
    return BranchManager(root_path=root, env=env)


@pytest.fixture()
def archive_mgr(root: Path, env: _MockEnv) -> ArchiveManager:
    return ArchiveManager(root_path=root, env=env)


# ===========================================================================
# BranchManager tests
# ===========================================================================


class TestBranchManagerCreate:
    @pytest.mark.asyncio
    async def test_issues_git_checkout_b(
        self, env: _MockEnv, branch_mgr: BranchManager
    ) -> None:
        await branch_mgr.create("feature-foo", "main")
        assert ("git", "checkout", "-b", "feature-foo", "main") in env.calls

    @pytest.mark.asyncio
    async def test_raises_on_nonzero_exit(
        self, env: _MockEnv, branch_mgr: BranchManager
    ) -> None:
        env.set_responses([(1, "", "branch already exists")])
        with pytest.raises(RuntimeError, match="branch already exists"):
            await branch_mgr.create("feature-foo", "main")


class TestBranchManagerMerge:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(
        self, env: _MockEnv, branch_mgr: BranchManager
    ) -> None:
        # checkout base branch succeeds, merge succeeds
        env.set_responses([(0, "", ""), (0, "", "")])
        result = await branch_mgr.merge("feature-foo", "main")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_on_conflict(
        self, env: _MockEnv, branch_mgr: BranchManager
    ) -> None:
        # checkout succeeds, merge fails with conflict
        env.set_responses([(0, "", ""), (1, "", "CONFLICT (content)")])
        result = await branch_mgr.merge("feature-foo", "main")
        assert result is False

    @pytest.mark.asyncio
    async def test_merge_does_not_raise_on_conflict(
        self, env: _MockEnv, branch_mgr: BranchManager
    ) -> None:
        env.set_responses([(0, "", ""), (1, "", "CONFLICT")])
        # Must not raise
        result = await branch_mgr.merge("feature-foo", "main")
        assert result is False

    @pytest.mark.asyncio
    async def test_raises_when_checkout_fails(
        self, env: _MockEnv, branch_mgr: BranchManager
    ) -> None:
        env.set_responses([(1, "", "error: pathspec 'main' did not match")])
        with pytest.raises(RuntimeError, match="pathspec"):
            await branch_mgr.merge("feature-foo", "main")

    @pytest.mark.asyncio
    async def test_checkout_base_branch_before_merge(
        self, env: _MockEnv, branch_mgr: BranchManager
    ) -> None:
        await branch_mgr.merge("feature-foo", "main")
        assert env.calls[0] == ("git", "checkout", "main")
        assert env.calls[1] == ("git", "merge", "--no-ff", "feature-foo")


class TestBranchManagerHasConflicts:
    @pytest.mark.asyncio
    async def test_returns_false_when_no_conflicts(
        self, env: _MockEnv, branch_mgr: BranchManager
    ) -> None:
        # dry-run merge succeeds (rc=0), then abort succeeds
        env.set_responses([(0, "", ""), (0, "", "")])
        result = await branch_mgr.has_conflicts("feature-foo")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_when_conflicts(
        self, env: _MockEnv, branch_mgr: BranchManager
    ) -> None:
        # dry-run merge fails => conflicts
        env.set_responses([(1, "", "CONFLICT"), (0, "", "")])
        result = await branch_mgr.has_conflicts("feature-foo")
        assert result is True

    @pytest.mark.asyncio
    async def test_aborts_merge_after_conflict(
        self, env: _MockEnv, branch_mgr: BranchManager
    ) -> None:
        env.set_responses([(1, "", "CONFLICT"), (0, "", "")])
        await branch_mgr.has_conflicts("feature-foo")
        assert ("git", "merge", "--abort") in env.calls

    @pytest.mark.asyncio
    async def test_aborts_merge_after_clean_dry_run(
        self, env: _MockEnv, branch_mgr: BranchManager
    ) -> None:
        env.set_responses([(0, "", ""), (0, "", "")])
        await branch_mgr.has_conflicts("feature-foo")
        assert ("git", "merge", "--abort") in env.calls


# ===========================================================================
# ArchiveManager tests
# ===========================================================================


class TestArchiveManagerArchive:
    def test_creates_archive_dir(
        self, tmp_path: Path, archive_mgr: ArchiveManager
    ) -> None:
        prd = tmp_path / "prd-my-feature.json"
        prd.write_text('{"project": "test"}')
        progress = tmp_path / "prd-my-feature.progress.md"
        progress.write_text("# progress")
        archive_base = tmp_path / "archive"

        dest = archive_mgr.archive(prd, progress, archive_base)

        today = date.today().isoformat()
        assert dest == archive_base / f"{today}-prd-my-feature"
        assert dest.is_dir()

    def test_copies_prd_into_archive(
        self, tmp_path: Path, archive_mgr: ArchiveManager
    ) -> None:
        prd = tmp_path / "prd-my-feature.json"
        prd.write_text('{"project": "test"}')
        progress = tmp_path / "progress.md"
        progress.write_text("# p")
        archive_base = tmp_path / "archive"

        dest = archive_mgr.archive(prd, progress, archive_base)

        assert (dest / "prd-my-feature.json").read_text() == '{"project": "test"}'

    def test_copies_progress_into_archive(
        self, tmp_path: Path, archive_mgr: ArchiveManager
    ) -> None:
        prd = tmp_path / "prd.json"
        prd.write_text("{}")
        progress = tmp_path / "progress.md"
        progress.write_text("# progress content")
        archive_base = tmp_path / "archive"

        dest = archive_mgr.archive(prd, progress, archive_base)

        assert (dest / "progress.md").read_text() == "# progress content"

    def test_creates_archive_dir_if_missing(
        self, tmp_path: Path, archive_mgr: ArchiveManager
    ) -> None:
        prd = tmp_path / "prd.json"
        prd.write_text("{}")
        progress = tmp_path / "progress.md"
        progress.write_text("")
        archive_base = tmp_path / "deeply" / "nested" / "archive"

        dest = archive_mgr.archive(prd, progress, archive_base)

        assert dest.is_dir()

    def test_raises_when_prd_missing(
        self, tmp_path: Path, archive_mgr: ArchiveManager
    ) -> None:
        prd = tmp_path / "nonexistent.json"
        progress = tmp_path / "progress.md"
        progress.write_text("")

        with pytest.raises(FileNotFoundError, match="nonexistent.json"):
            archive_mgr.archive(prd, progress, tmp_path / "archive")

    def test_raises_when_progress_missing(
        self, tmp_path: Path, archive_mgr: ArchiveManager
    ) -> None:
        prd = tmp_path / "prd.json"
        prd.write_text("{}")
        progress = tmp_path / "nonexistent.md"

        with pytest.raises(FileNotFoundError, match="nonexistent.md"):
            archive_mgr.archive(prd, progress, tmp_path / "archive")

    def test_archive_dir_name_uses_today(
        self, tmp_path: Path, archive_mgr: ArchiveManager
    ) -> None:
        prd = tmp_path / "prd-sample.json"
        prd.write_text("{}")
        progress = tmp_path / "p.md"
        progress.write_text("")
        archive_base = tmp_path / "archive"

        dest = archive_mgr.archive(prd, progress, archive_base)

        today = date.today().isoformat()
        assert dest.name.startswith(today)

"""Tests for WorktreeManager."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Literal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from harness.core.models.prd import Story
from harness.core.worktree import WorktreeManager
from harness.execution.models import Context


# ---------------------------------------------------------------------------
# Minimal mock ExecutionEnvironment
# ---------------------------------------------------------------------------


class _MockEnv:
    """A minimal ExecutionEnvironment whose execute() is controllable."""

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
def manager(root: Path, env: _MockEnv) -> WorktreeManager:
    return WorktreeManager(root_path=root, env=env)


def _worktree(root: Path, story_id: str = "US-005") -> Path:
    return root / ".harness" / "worktrees" / story_id


# ---------------------------------------------------------------------------
# TestGetPath
# ---------------------------------------------------------------------------


class TestGetPath:
    def test_returns_none_when_not_exists(self, manager: WorktreeManager) -> None:
        assert manager.get_path("US-005") is None

    def test_returns_path_when_dir_exists(
        self, root: Path, manager: WorktreeManager
    ) -> None:
        path = _worktree(root)
        path.mkdir(parents=True)
        assert manager.get_path("US-005") == path

    def test_returns_none_for_file_not_dir(
        self, root: Path, manager: WorktreeManager
    ) -> None:
        path = _worktree(root)
        path.parent.mkdir(parents=True)
        path.touch()
        assert manager.get_path("US-005") is None


# ---------------------------------------------------------------------------
# TestCreate
# ---------------------------------------------------------------------------


class TestCreate:
    @pytest.mark.asyncio
    async def test_issues_git_worktree_add(
        self, root: Path, env: _MockEnv, manager: WorktreeManager
    ) -> None:
        await manager.create("US-005", "worktree-us-005")
        expected = (
            "git",
            "worktree",
            "add",
            "-b",
            "worktree-us-005",
            str(_worktree(root)),
        )
        assert expected in env.calls

    @pytest.mark.asyncio
    async def test_returns_worktree_path(
        self, root: Path, manager: WorktreeManager
    ) -> None:
        path = await manager.create("US-005", "worktree-us-005")
        assert path == _worktree(root)

    @pytest.mark.asyncio
    async def test_creates_parent_dir(
        self, root: Path, manager: WorktreeManager
    ) -> None:
        await manager.create("US-005", "worktree-us-005")
        assert (root / ".harness" / "worktrees").is_dir()

    @pytest.mark.asyncio
    async def test_raises_on_git_failure(
        self, env: _MockEnv, manager: WorktreeManager
    ) -> None:
        env.set_responses([(1, "", "fatal: branch already exists")])
        with pytest.raises(RuntimeError, match="git worktree add failed"):
            await manager.create("US-005", "worktree-us-005")

    @pytest.mark.asyncio
    async def test_symlinks_env_when_present(
        self, root: Path, env: _MockEnv
    ) -> None:
        env_file = root / ".env"
        env_file.write_text("SECRET=123")
        worktree_path = _worktree(root)
        worktree_path.mkdir(parents=True)

        mgr = WorktreeManager(root_path=root, env=env)
        await mgr.create("US-005", "worktree-us-005")

        env_link = worktree_path / ".env"
        assert env_link.is_symlink()
        assert env_link.resolve() == env_file.resolve()

    @pytest.mark.asyncio
    async def test_no_symlink_when_env_absent(
        self, root: Path, manager: WorktreeManager
    ) -> None:
        worktree_path = _worktree(root)
        worktree_path.mkdir(parents=True)
        await manager.create("US-005", "worktree-us-005")
        assert not (worktree_path / ".env").exists()

    @pytest.mark.asyncio
    async def test_dep_install_runs_in_worktree(
        self, root: Path, env: _MockEnv
    ) -> None:
        worktree_path = _worktree(root)
        worktree_path.mkdir(parents=True)

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"", b""))

        with patch(
            "harness.core.worktree.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=mock_proc,
        ) as mock_exec:
            mgr = WorktreeManager(
                root_path=root, env=env, dep_install_command=["uv", "sync"]
            )
            await mgr.create("US-005", "worktree-us-005")

        mock_exec.assert_called_once()
        _, kwargs = mock_exec.call_args
        assert kwargs.get("cwd") == worktree_path

    @pytest.mark.asyncio
    async def test_dep_install_skipped_when_not_configured(
        self, root: Path, env: _MockEnv
    ) -> None:
        worktree_path = _worktree(root)
        worktree_path.mkdir(parents=True)

        with patch(
            "harness.core.worktree.asyncio.create_subprocess_exec"
        ) as mock_exec:
            mgr = WorktreeManager(root_path=root, env=env, dep_install_command=None)
            await mgr.create("US-005", "worktree-us-005")

        mock_exec.assert_not_called()

    @pytest.mark.asyncio
    async def test_dep_install_failure_raises(
        self, root: Path, env: _MockEnv
    ) -> None:
        worktree_path = _worktree(root)
        worktree_path.mkdir(parents=True)

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"uv: error"))

        with patch(
            "harness.core.worktree.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=mock_proc,
        ):
            mgr = WorktreeManager(
                root_path=root, env=env, dep_install_command=["uv", "sync"]
            )
            with pytest.raises(RuntimeError, match="dep-install failed"):
                await mgr.create("US-005", "worktree-us-005")


# ---------------------------------------------------------------------------
# TestTeardown
# ---------------------------------------------------------------------------


class TestTeardown:
    @pytest.mark.asyncio
    async def test_issues_git_worktree_remove(
        self, root: Path, env: _MockEnv, manager: WorktreeManager
    ) -> None:
        await manager.teardown("US-005")
        expected = (
            "git",
            "worktree",
            "remove",
            "--force",
            str(_worktree(root)),
        )
        assert expected in env.calls

    @pytest.mark.asyncio
    async def test_on_failure_removes_leftover_dir(
        self, root: Path, env: _MockEnv, manager: WorktreeManager
    ) -> None:
        env.set_responses([(1, "", "error: not a worktree")])
        worktree_path = _worktree(root)
        worktree_path.mkdir(parents=True)
        (worktree_path / "leftover.txt").write_text("leftover")

        await manager.teardown("US-005")

        assert not worktree_path.exists()

    @pytest.mark.asyncio
    async def test_on_failure_prunes_stale_refs(
        self, root: Path, env: _MockEnv, manager: WorktreeManager
    ) -> None:
        env.set_responses([(1, "", "error: not a worktree")])
        await manager.teardown("US-005")
        assert ("git", "worktree", "prune") in env.calls

    @pytest.mark.asyncio
    async def test_success_does_not_prune(
        self, root: Path, env: _MockEnv, manager: WorktreeManager
    ) -> None:
        await manager.teardown("US-005")
        assert ("git", "worktree", "prune") not in env.calls

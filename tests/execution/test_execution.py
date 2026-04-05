"""Tests for execution environment protocol and implementations."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from harness.core.models.prd import Story
from harness.execution.base import Context, ExecutionEnvironment
from harness.execution.container import ContainerEnvironment
from harness.execution.local import LocalWorktreeEnvironment


def _make_story(story_id: str = "US-003") -> Story:
    return Story(
        id=story_id,
        title="Test Story",
        description="A test story",
        acceptanceCriteria=[],
        priority=1,
    )


def _mock_git_proc(returncode: int = 0) -> MagicMock:
    """Return a mock asyncio Process that reports a git success/failure."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(b"", b""))
    return proc


class TestContext:
    def test_fields(self, tmp_path: Path) -> None:
        ctx = Context(
            root_path=tmp_path,
            worktree_path=tmp_path / "worktree",
            branch_name="worktree-us-003",
            story_id="US-003",
        )
        assert ctx.root_path == tmp_path
        assert ctx.story_id == "US-003"
        assert ctx.branch_name == "worktree-us-003"


class TestExecutionEnvironmentProtocol:
    def test_local_satisfies_protocol(self, tmp_path: Path) -> None:
        env = LocalWorktreeEnvironment(tmp_path)
        assert isinstance(env, ExecutionEnvironment)

    def test_network_policy_default(self, tmp_path: Path) -> None:
        env = LocalWorktreeEnvironment(tmp_path)
        assert env.network_policy == "full"


class TestLocalWorktreeEnvironment:
    def test_get_root(self, tmp_path: Path) -> None:
        env = LocalWorktreeEnvironment(tmp_path)
        assert env.get_root() == tmp_path

    @pytest.mark.asyncio
    async def test_setup_returns_context(self, tmp_path: Path) -> None:
        with patch(
            "harness.execution.local.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=_mock_git_proc(0),
        ):
            env = LocalWorktreeEnvironment(tmp_path)
            story = _make_story("US-003")
            ctx = await env.setup(story)
        assert isinstance(ctx, Context)
        assert ctx.story_id == "US-003"
        assert ctx.root_path == tmp_path
        assert ctx.worktree_path == tmp_path / ".harness" / "worktrees" / "US-003"
        assert ctx.branch_name == "worktree-us-003"

    @pytest.mark.asyncio
    async def test_execute_returns_tuple(self, tmp_path: Path) -> None:
        # Patch only for the git worktree add during setup, then let execute run real commands
        git_proc = _mock_git_proc(0)
        with patch(
            "harness.execution.local.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=git_proc,
        ) as mock_exec:
            env = LocalWorktreeEnvironment(tmp_path)
            story = _make_story()
            ctx = await env.setup(story)
            ctx.worktree_path.mkdir(parents=True, exist_ok=True)
            mock_exec.return_value = None  # stop mocking for next call

        returncode, stdout, stderr = await env.execute("echo", "hello")
        assert returncode == 0
        assert "hello" in stdout

    @pytest.mark.asyncio
    async def test_teardown_clears_context(self, tmp_path: Path) -> None:
        with patch(
            "harness.execution.local.asyncio.create_subprocess_exec",
            new_callable=AsyncMock,
            return_value=_mock_git_proc(0),
        ):
            env = LocalWorktreeEnvironment(tmp_path)
            story = _make_story()
            await env.setup(story)
            await env.teardown()
        assert env._context is None

    @pytest.mark.asyncio
    async def test_execute_without_setup_uses_root(self, tmp_path: Path) -> None:
        env = LocalWorktreeEnvironment(tmp_path)
        returncode, stdout, _ = await env.execute("pwd")
        assert returncode == 0
        assert str(tmp_path) in stdout.strip()



class TestContainerEnvironment:
    @pytest.mark.asyncio
    async def test_setup_raises_not_implemented(self, tmp_path: Path) -> None:
        env = ContainerEnvironment(tmp_path)
        with pytest.raises(NotImplementedError, match="ContainerEnvironment"):
            await env.setup(_make_story())

    def test_get_root_raises_not_implemented(self, tmp_path: Path) -> None:
        env = ContainerEnvironment(tmp_path)
        with pytest.raises(NotImplementedError, match="ContainerEnvironment"):
            env.get_root()

    @pytest.mark.asyncio
    async def test_execute_raises_not_implemented(self, tmp_path: Path) -> None:
        env = ContainerEnvironment(tmp_path)
        with pytest.raises(NotImplementedError, match="ContainerEnvironment"):
            await env.execute("echo")

    @pytest.mark.asyncio
    async def test_teardown_raises_not_implemented(self, tmp_path: Path) -> None:
        env = ContainerEnvironment(tmp_path)
        with pytest.raises(NotImplementedError, match="ContainerEnvironment"):
            await env.teardown()

    def test_network_policy(self, tmp_path: Path) -> None:
        env = ContainerEnvironment(tmp_path)
        assert env.network_policy == "restricted"

"""Execution environment abstraction (local worktree; container in V2)."""

from harness.execution.base import ExecutionEnvironment
from harness.execution.container import ContainerEnvironment
from harness.execution.local import LocalWorktreeEnvironment
from harness.execution.models import Context

__all__ = [
    "Context",
    "ContainerEnvironment",
    "ExecutionEnvironment",
    "LocalWorktreeEnvironment",
]

"""ExecutionEnvironment protocol."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from harness.core.models.prd import Story
from harness.execution.models import Context

__all__ = ["Context", "ExecutionEnvironment"]


@runtime_checkable
class ExecutionEnvironment(Protocol):
    network_policy: Literal["full", "restricted", "gapped"]

    async def setup(self, story: Story) -> Context: ...

    async def execute(
        self, command: str, *args: str
    ) -> tuple[int, str, str]: ...

    def get_root(self) -> Path: ...

    async def teardown(self) -> None: ...

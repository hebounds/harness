"""ContainerEnvironment — stub for future container-based execution."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from harness.core.models.prd import Story
from harness.execution.models import Context


class ContainerEnvironment:
    """Stub ExecutionEnvironment for container-based isolation (V2)."""

    network_policy: Literal["full", "restricted", "gapped"] = "restricted"

    def __init__(self, root_path: Path) -> None:
        self._root_path = root_path

    def get_root(self) -> Path:
        raise NotImplementedError(
            "ContainerEnvironment is not yet implemented. Use LocalWorktreeEnvironment."
        )

    async def setup(self, story: Story) -> Context:
        raise NotImplementedError(
            "ContainerEnvironment.setup() is not yet implemented. Use LocalWorktreeEnvironment."
        )

    async def execute(self, command: str, *args: str) -> tuple[int, str, str]:
        raise NotImplementedError(
            "ContainerEnvironment.execute() is not yet implemented. Use LocalWorktreeEnvironment."
        )

    async def teardown(self) -> None:
        raise NotImplementedError(
            "ContainerEnvironment.teardown() is not yet implemented. Use LocalWorktreeEnvironment."
        )

"""Agent orchestration loop (full implementation: US-002, US-007)."""

from __future__ import annotations

from harness.config import HarnessConfig
from harness.core.models.prd import Prd, Story


class Orchestrator:
    """Manages the full agent lifecycle for a set of PRD stories.

    V1 implementation (US-002, US-007) will add:
      - ClaimManager  — atomic story claiming
      - WorktreeManager — git worktree creation/teardown
      - PromptBuilder   — minimal per-story system prompt
      - AgentOutputParser — real-time completion/failure detection
      - VerificationGate  — lint + typecheck before merge
      - BranchManager   — feature branch merge-back
      - parallel dispatch via asyncio.gather (up to config.max_parallel_agents)
    """

    def __init__(self, config: HarnessConfig, prd: Prd) -> None:
        self._config = config
        self._prd = prd

    async def run(self, stories: list[Story]) -> None:
        """Execute the agent loop for the given stories.

        Not yet implemented — placeholder for US-002/US-007.
        """
        raise NotImplementedError(
            "Orchestrator.run() is not yet implemented. "
            "See US-002 (Deterministic Lifecycle Manager) and "
            "US-007 (Multi-Agent Workflow Orchestrator)."
        )

    async def cleanup(self) -> None:
        """Release all claims and tear down any live worktrees.

        Not yet implemented — placeholder for US-002.
        """

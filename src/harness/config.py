"""Harness configuration via Pydantic models."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ProfileConfig(BaseModel):
    """Configuration for a language profile."""

    language: str
    enabled: bool = True
    lint_command: str | None = None
    format_command: str | None = None
    typecheck_command: str | None = None


class HarnessConfig(BaseModel):
    """Root configuration model for the harness system."""

    # Agent runtime
    runtime: Literal["copilot"] = "copilot"
    model: str = "claude-sonnet-4.6"

    # Iteration limits
    max_iterations: int = Field(default=10, ge=1)
    max_retries: int = Field(default=2, ge=0)
    max_parallel_agents: int = Field(default=1, ge=1)

    # Paths
    prd_path: Path = Path("tasks/prd.json")
    progress_dir: Path = Path("progress")
    claims_dir: Path = Path("tasks/claims")
    worktree_base: Path = Path(".worktrees")
    harness_dir: Path = Path(".harness")

    # Prompt
    max_prompt_tokens: int = Field(default=4000, ge=100)
    completion_signal: str = "<promise>COMPLETE</promise>"
    failure_signal: str = "<promise>FAILED</promise>"

    # Language profiles
    language_profiles: list[ProfileConfig] = Field(default_factory=list[ProfileConfig])
    auto_detect_profiles: bool = True

    # Tool permissions
    tool_allowlist: list[str] = Field(default_factory=list)
    tool_denylist: list[str] = Field(default_factory=list)

    # Verification
    verification_command: str | None = None
    verification_timeout: int = Field(default=300, ge=10)  # seconds

    # Memory
    embedding_provider: Literal["fastembed", "openai"] = "fastembed"
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # Stale claim timeout in seconds (default 30 min)
    claim_stale_timeout: int = Field(default=1800, ge=60)


DEFAULT_CONFIG_TEMPLATE = '''\
"""Harness configuration for this project."""

from harness.config import HarnessConfig, ProfileConfig

config = HarnessConfig(
    runtime="copilot",
    model="claude-sonnet-4.6",
    max_iterations=10,
    max_retries=2,
    max_parallel_agents=1,
    prd_path="tasks/prd.json",
    max_prompt_tokens=4000,
    auto_detect_profiles=True,
)
'''

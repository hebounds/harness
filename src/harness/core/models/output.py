"""Agent output models (US-012)."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CompletionSignal(str, Enum):
    COMPLETE = "complete"
    FAILED = "failed"
    PARTIAL = "partial"


class AgentResult(BaseModel):
    signal: CompletionSignal
    files_modified: list[str] = Field(default_factory=list)
    has_uncommitted_changes: bool = False
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0

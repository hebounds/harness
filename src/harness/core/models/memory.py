"""Memory result model (US-011)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MemoryResult(BaseModel):
    content: str
    source: str  # file path or entry identifier
    category: str  # progress, pattern, code
    score: float  # similarity score
    metadata: dict[str, Any] = Field(default_factory=dict)

"""Progress entry model (US-003)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProgressEntry(BaseModel):
    story_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    status: str  # completed, failed, partial
    files_changed: list[str] = Field(default_factory=list)
    summary: str = ""
    details: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

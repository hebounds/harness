"""Verification gate models (US-013)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from harness.profiles.base import Diagnostic


class GateResult(BaseModel):
    passed: bool
    diagnostics: list[Diagnostic] = Field(default_factory=list)
    test_output: str = ""
    checks_run: list[str] = Field(default_factory=list)
    checks_passed: list[str] = Field(default_factory=list)
    checks_failed: list[str] = Field(default_factory=list)

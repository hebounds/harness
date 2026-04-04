"""Base types and Protocol for language profiles (US-005)."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


class Diagnostic(BaseModel):
    file: Path
    line: int
    column: int
    message: str
    severity: Severity = Severity.ERROR
    code: str | None = None
    source: str | None = None


class Symbol(BaseModel):
    name: str
    kind: str  # function, class, method, variable, etc.
    file: Path
    line: int
    end_line: int | None = None
    children: list[Symbol] = Field(default_factory=list)  # pyright: ignore[reportUnknownVariableType]


class Location(BaseModel):
    file: Path
    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None
    context: str = ""  # surrounding code snippet


@runtime_checkable
class LanguageProfile(Protocol):
    """Protocol every language profile must satisfy.

    Each implementation shells out to the language's native toolchain
    (tsc, mypy, ruff, go vet, cargo check, …), parses structured output,
    and returns typed results — no special-cased programmatic APIs.
    """

    def lint(self, file: Path) -> list[Diagnostic]: ...

    def format(self, file: Path) -> str: ...

    def typecheck(self, project: Path) -> list[Diagnostic]: ...

    def get_symbols(self, file: Path) -> list[Symbol]: ...

    def find_references(self, symbol: str, project: Path) -> list[Location]: ...

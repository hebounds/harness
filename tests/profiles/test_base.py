"""Tests for Diagnostic and Severity models from profiles.base."""

from __future__ import annotations

from pathlib import Path

from harness.profiles.base import Diagnostic, Severity


class TestDiagnosticDefaults:
    def test_required_fields(self) -> None:
        diag = Diagnostic(file=Path("src/foo.py"), line=10, column=4, message="Undefined 'bar'")
        assert diag.file == Path("src/foo.py")
        assert diag.line == 10
        assert diag.column == 4
        assert diag.message == "Undefined 'bar'"

    def test_default_severity(self) -> None:
        diag = Diagnostic(file=Path("f.py"), line=1, column=0, message="msg")
        assert diag.severity == Severity.ERROR

    def test_default_code_none(self) -> None:
        assert Diagnostic(file=Path("f.py"), line=1, column=0, message="msg").code is None

    def test_default_source_none(self) -> None:
        assert Diagnostic(file=Path("f.py"), line=1, column=0, message="msg").source is None


class TestDiagnosticCustomValues:
    def test_warning_severity(self) -> None:
        diag = Diagnostic(
            file=Path("f.py"), line=1, column=0, message="msg", severity=Severity.WARNING
        )
        assert diag.severity == Severity.WARNING

    def test_code(self) -> None:
        diag = Diagnostic(file=Path("f.py"), line=1, column=0, message="msg", code="E501")
        assert diag.code == "E501"

    def test_source(self) -> None:
        diag = Diagnostic(file=Path("f.py"), line=1, column=0, message="msg", source="ruff")
        assert diag.source == "ruff"


class TestDiagnosticSerialization:
    def test_json_round_trip(self) -> None:
        diag = Diagnostic(
            file=Path("src/module.py"),
            line=42,
            column=8,
            message="Type error",
            severity=Severity.ERROR,
            code="mypy-error",
            source="mypy",
        )
        assert Diagnostic.model_validate_json(diag.model_dump_json()) == diag


class TestSeverityEnum:
    def test_error_value(self) -> None:
        assert Severity.ERROR == "error"

    def test_warning_value(self) -> None:
        assert Severity.WARNING == "warning"

    def test_info_value(self) -> None:
        assert Severity.INFO == "info"

    def test_hint_value(self) -> None:
        assert Severity.HINT == "hint"

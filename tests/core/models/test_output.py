"""Tests for AgentResult and CompletionSignal models."""

from __future__ import annotations

from harness.core.models.output import AgentResult, CompletionSignal


class TestAgentResultDefaults:
    def test_signal_stored(self) -> None:
        assert AgentResult(signal=CompletionSignal.COMPLETE).signal == CompletionSignal.COMPLETE

    def test_default_files_modified(self) -> None:
        assert AgentResult(signal=CompletionSignal.COMPLETE).files_modified == []

    def test_default_return_code(self) -> None:
        assert AgentResult(signal=CompletionSignal.COMPLETE).return_code == 0

    def test_default_has_uncommitted_changes(self) -> None:
        assert AgentResult(signal=CompletionSignal.COMPLETE).has_uncommitted_changes is False


class TestAgentResultSignals:
    def test_failed(self) -> None:
        assert AgentResult(signal=CompletionSignal.FAILED).signal == CompletionSignal.FAILED

    def test_partial(self) -> None:
        assert AgentResult(signal=CompletionSignal.PARTIAL).signal == CompletionSignal.PARTIAL


class TestAgentResultCustomValues:
    def test_files_modified(self) -> None:
        result = AgentResult(
            signal=CompletionSignal.COMPLETE, files_modified=["src/a.py", "src/b.py"]
        )
        assert result.files_modified == ["src/a.py", "src/b.py"]

    def test_has_uncommitted_changes(self) -> None:
        result = AgentResult(signal=CompletionSignal.COMPLETE, has_uncommitted_changes=True)
        assert result.has_uncommitted_changes is True

    def test_stdout_and_stderr(self) -> None:
        result = AgentResult(signal=CompletionSignal.COMPLETE, stdout="Done", stderr="warn")
        assert result.stdout == "Done"
        assert result.stderr == "warn"

    def test_return_code(self) -> None:
        result = AgentResult(signal=CompletionSignal.FAILED, return_code=1)
        assert result.return_code == 1


class TestAgentResultSerialization:
    def test_json_round_trip(self) -> None:
        result = AgentResult(
            signal=CompletionSignal.FAILED,
            files_modified=["main.py"],
            return_code=1,
            stderr="error: undefined variable",
        )
        assert AgentResult.model_validate_json(result.model_dump_json()) == result


class TestCompletionSignalEnum:
    def test_complete_value(self) -> None:
        assert CompletionSignal.COMPLETE == "complete"

    def test_failed_value(self) -> None:
        assert CompletionSignal.FAILED == "failed"

    def test_partial_value(self) -> None:
        assert CompletionSignal.PARTIAL == "partial"

"""Tests for the harness init CLI command."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from harness.cli import app
from harness.config import DEFAULT_CONFIG_TEMPLATE

runner = CliRunner()


class TestInitCreatesFiles:
    def test_creates_config_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / "harness_config.py").exists()

    def test_config_content_matches_template(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        assert (tmp_path / "harness_config.py").read_text() == DEFAULT_CONFIG_TEMPLATE

    def test_creates_progress_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        assert (tmp_path / "progress").is_dir()

    def test_creates_claims_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        assert (tmp_path / "tasks" / "claims").is_dir()

    def test_creates_harness_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        runner.invoke(app, ["init"])
        assert (tmp_path / ".harness").is_dir()

    def test_custom_path_option(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        custom = tmp_path / "custom_config.py"
        result = runner.invoke(app, ["init", "--path", str(custom)])
        assert result.exit_code == 0
        assert custom.exists()


class TestInitIdempotency:
    def test_aborts_when_overwrite_denied(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "harness_config.py"
        config_file.write_text("# existing content")

        result = runner.invoke(app, ["init"], input="n\n")
        assert result.exit_code != 0
        assert config_file.read_text() == "# existing content"

    def test_overwrites_when_confirmed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "harness_config.py"
        config_file.write_text("# existing content")

        result = runner.invoke(app, ["init"], input="y\n")
        assert result.exit_code == 0
        assert config_file.read_text() == DEFAULT_CONFIG_TEMPLATE

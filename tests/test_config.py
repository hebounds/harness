"""Tests for HarnessConfig Pydantic model."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from harness.config import DEFAULT_CONFIG_TEMPLATE, HarnessConfig


class TestDefaults:
    def test_runtime(self) -> None:
        assert HarnessConfig().runtime == "copilot"

    def test_model(self) -> None:
        assert HarnessConfig().model == "claude-sonnet-4.6"

    def test_max_iterations(self) -> None:
        assert HarnessConfig().max_iterations == 10

    def test_max_retries(self) -> None:
        assert HarnessConfig().max_retries == 2

    def test_max_parallel_agents(self) -> None:
        assert HarnessConfig().max_parallel_agents == 1

    def test_prd_path(self) -> None:
        assert HarnessConfig().prd_path == Path("tasks/prd.json")

    def test_max_prompt_tokens(self) -> None:
        assert HarnessConfig().max_prompt_tokens == 4000

    def test_tool_allowlist(self) -> None:
        assert HarnessConfig().tool_allowlist == []

    def test_tool_denylist(self) -> None:
        assert HarnessConfig().tool_denylist == []

    def test_verification_command(self) -> None:
        assert HarnessConfig().verification_command is None

    def test_language_profiles(self) -> None:
        assert HarnessConfig().language_profiles == []


class TestCustomValues:
    def test_model(self) -> None:
        assert HarnessConfig(model="gpt-4o").model == "gpt-4o"

    def test_max_iterations(self) -> None:
        assert HarnessConfig(max_iterations=5).max_iterations == 5

    def test_prd_path(self) -> None:
        assert HarnessConfig(prd_path=Path("custom/prd.json")).prd_path == Path("custom/prd.json")

    def test_tool_allowlist(self) -> None:
        cfg = HarnessConfig(tool_allowlist=["read_file", "write_file"])
        assert cfg.tool_allowlist == ["read_file", "write_file"]

    def test_verification_command(self) -> None:
        cfg = HarnessConfig(verification_command="pytest tests/")
        assert cfg.verification_command == "pytest tests/"

    def test_max_parallel_agents(self) -> None:
        assert HarnessConfig(max_parallel_agents=4).max_parallel_agents == 4


class TestValidation:
    def test_max_iterations_below_minimum(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            HarnessConfig(max_iterations=0)
        assert any(e["loc"] == ("max_iterations",) for e in exc_info.value.errors())

    def test_max_retries_below_minimum(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            HarnessConfig(max_retries=-1)
        assert any(e["loc"] == ("max_retries",) for e in exc_info.value.errors())

    def test_max_parallel_agents_below_minimum(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            HarnessConfig(max_parallel_agents=0)
        assert any(e["loc"] == ("max_parallel_agents",) for e in exc_info.value.errors())

    def test_max_prompt_tokens_below_minimum(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            HarnessConfig(max_prompt_tokens=50)
        assert any(e["loc"] == ("max_prompt_tokens",) for e in exc_info.value.errors())

    def test_invalid_runtime(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            HarnessConfig(runtime="invalid")  # type: ignore[arg-type]
        assert any(e["loc"] == ("runtime",) for e in exc_info.value.errors())

    def test_invalid_embedding_provider(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            HarnessConfig(embedding_provider="unknown")  # type: ignore[arg-type]
        assert any(e["loc"] == ("embedding_provider",) for e in exc_info.value.errors())


class TestSerialization:
    def test_json_round_trip(self) -> None:
        cfg = HarnessConfig(
            model="gpt-4o",
            max_iterations=7,
            tool_allowlist=["read_file"],
            verification_command="pytest",
        )
        assert HarnessConfig.model_validate_json(cfg.model_dump_json()) == cfg

    def test_dict_round_trip(self) -> None:
        cfg = HarnessConfig(max_retries=3, max_parallel_agents=2)
        assert HarnessConfig.model_validate(cfg.model_dump()) == cfg


class TestImportlibLoad:
    def test_loads_from_generated_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config scaffolded by init loads and validates via importlib."""
        config_file = tmp_path / "harness_config.py"
        config_file.write_text(DEFAULT_CONFIG_TEMPLATE)

        module_name = "_harness_config_importlib_test"
        spec = importlib.util.spec_from_file_location(module_name, config_file)
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        try:
            assert isinstance(module.config, HarnessConfig)
        finally:
            del sys.modules[module_name]

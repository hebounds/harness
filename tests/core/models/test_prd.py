"""Tests for Story and Prd Pydantic models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.core.models.prd import Prd, Story, StoryStatus


def _story(story_id: str = "US-001", **kwargs: object) -> Story:
    return Story(id=story_id, title="Title", description="Description", **kwargs)  # type: ignore[arg-type]


class TestStoryDefaults:
    def test_priority(self) -> None:
        assert _story().priority == 1

    def test_passes(self) -> None:
        assert _story().passes is False

    def test_notes(self) -> None:
        assert _story().notes == ""

    def test_depends_on(self) -> None:
        assert _story().depends_on == []

    def test_parallel_group(self) -> None:
        assert _story().parallel_group is None

    def test_acceptance_criteria(self) -> None:
        assert _story().acceptance_criteria == []

    def test_status(self) -> None:
        assert _story().status == StoryStatus.NOT_STARTED


class TestStoryCamelCaseAliases:
    def test_acceptance_criteria_alias(self) -> None:
        story = Story(
            id="US-001",
            title="T",
            description="D",
            acceptanceCriteria=["Criterion A"],  # type: ignore[call-arg]
        )
        assert story.acceptance_criteria == ["Criterion A"]

    def test_depends_on_alias(self) -> None:
        story = Story(id="US-002", title="T", description="D", dependsOn=["US-001"])  # type: ignore[call-arg]
        assert story.depends_on == ["US-001"]

    def test_parallel_group_alias(self) -> None:
        story = Story(id="US-002", title="T", description="D", parallelGroup="wave-1")  # type: ignore[call-arg]
        assert story.parallel_group == "wave-1"

    def test_python_field_names_work(self) -> None:
        story = _story(depends_on=["US-001"], parallel_group="wave-1")
        assert story.depends_on == ["US-001"]
        assert story.parallel_group == "wave-1"


class TestStorySerialization:
    def test_json_round_trip(self) -> None:
        story = _story(
            acceptance_criteria=["AC1"],
            priority=2,
            passes=True,
            notes="note",
            depends_on=["US-001"],
            parallel_group="group-a",
        )
        assert Story.model_validate_json(story.model_dump_json()) == story

    def test_dump_by_alias_uses_camel(self) -> None:
        story = _story(depends_on=["US-000"])
        data = story.model_dump(by_alias=True)
        assert "dependsOn" in data
        assert data["dependsOn"] == ["US-000"]

    def test_load_from_camel_json(self) -> None:
        raw = json.dumps(
            {
                "id": "US-001",
                "title": "Title",
                "description": "Desc",
                "acceptanceCriteria": ["AC"],
                "priority": 3,
                "passes": False,
                "notes": "",
                "dependsOn": ["US-000"],
                "parallelGroup": None,
            }
        )
        story = Story.model_validate_json(raw)
        assert story.acceptance_criteria == ["AC"]
        assert story.depends_on == ["US-000"]


class TestPrdConstruction:
    def test_python_field_names(self) -> None:
        prd = Prd(
            project="MyProject",
            branch_name="feature/x",
            description="A PRD",
            user_stories=[_story()],
        )
        assert prd.project == "MyProject"
        assert prd.branch_name == "feature/x"

    def test_camel_aliases(self) -> None:
        prd = Prd.model_validate(
            {
                "project": "MyProject",
                "branchName": "feature/x",
                "description": "A PRD",
                "userStories": [{"id": "US-001", "title": "T", "description": "D"}],
            }
        )
        assert prd.branch_name == "feature/x"
        assert len(prd.user_stories) == 1

    def test_json_round_trip(self) -> None:
        prd = Prd(
            project="P",
            branch_name="main",
            description="Desc",
            user_stories=[_story("US-001"), _story("US-002")],
        )
        assert Prd.model_validate_json(prd.model_dump_json()) == prd


class TestPrdGetStory:
    def test_found(self) -> None:
        story = _story("US-042")
        prd = Prd(project="P", branch_name="b", description="D", user_stories=[story])
        assert prd.get_story("US-042") is not None

    def test_not_found(self) -> None:
        prd = Prd(project="P", branch_name="b", description="D", user_stories=[_story()])
        assert prd.get_story("US-999") is None


class TestPrdReadyStories:
    def test_no_deps_all_ready(self) -> None:
        s1, s2 = _story("US-001"), _story("US-002")
        prd = Prd(project="P", branch_name="b", description="D", user_stories=[s1, s2])
        assert {s.id for s in prd.ready_stories()} == {"US-001", "US-002"}

    def test_unsatisfied_dep_blocks_story(self) -> None:
        s1 = _story("US-001")
        s2 = _story("US-002", depends_on=["US-001"])
        prd = Prd(project="P", branch_name="b", description="D", user_stories=[s1, s2])
        assert {s.id for s in prd.ready_stories(completed=set())} == {"US-001"}

    def test_satisfied_dep_unblocks_story(self) -> None:
        s1 = _story("US-001")
        s2 = _story("US-002", depends_on=["US-001"])
        prd = Prd(project="P", branch_name="b", description="D", user_stories=[s1, s2])
        assert "US-002" in {s.id for s in prd.ready_stories(completed={"US-001"})}

    def test_passed_story_excluded(self) -> None:
        prd = Prd(project="P", branch_name="b", description="D", user_stories=[_story(passes=True)])
        assert prd.ready_stories() == []

    def test_failed_story_excluded(self) -> None:
        prd = Prd(
            project="P",
            branch_name="b",
            description="D",
            user_stories=[_story(status=StoryStatus.FAILED)],
        )
        assert prd.ready_stories() == []

    def test_deserialise_real_prd_file(self) -> None:
        prd_file = Path(__file__).parent.parent / "prd-agent-harness.json"
        if not prd_file.exists():
            pytest.skip("prd-agent-harness.json not present")
        prd = Prd.model_validate_json(prd_file.read_text())
        assert prd.project == "Harness"
        assert len(prd.user_stories) > 0

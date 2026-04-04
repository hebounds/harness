"""PRD domain models — the shared kernel imported by all harness modules."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class StoryStatus(str, Enum):
    NOT_STARTED = "not-started"
    IN_PROGRESS = "in-progress"
    PASSED = "passed"
    FAILED = "failed"


class Story(BaseModel):
    id: str
    title: str
    description: str
    acceptance_criteria: list[str] = Field(alias="acceptanceCriteria", default_factory=list)
    priority: int = 1
    passes: bool = False
    status: StoryStatus = StoryStatus.NOT_STARTED
    notes: str = ""
    depends_on: list[str] = Field(alias="dependsOn", default_factory=list)
    parallel_group: str | None = Field(alias="parallelGroup", default=None)

    model_config = {"populate_by_name": True}


class Prd(BaseModel):
    project: str
    branch_name: str = Field(alias="branchName")
    description: str
    user_stories: list[Story] = Field(alias="userStories")

    model_config = {"populate_by_name": True}

    def get_story(self, story_id: str) -> Story | None:
        for story in self.user_stories:
            if story.id == story_id:
                return story
        return None

    def ready_stories(self, completed: set[str] | None = None) -> list[Story]:
        """Return stories whose dependencies are all satisfied."""
        done = completed or set()
        return [
            s
            for s in self.user_stories
            if not s.passes
            and s.status != StoryStatus.FAILED
            and all(dep in done for dep in s.depends_on)
        ]

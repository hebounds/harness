"""DAG-based story scheduler (full implementation: US-010)."""

from __future__ import annotations

import graphlib
from dataclasses import dataclass, field

from harness.core.models.prd import Prd, Story


@dataclass
class ExecutionPlan:
    """Resolved execution order: parallelisable waves and the critical path."""

    waves: list[list[Story]] = field(default_factory=list[list[Story]])
    critical_path: list[str] = field(default_factory=list[str])


class DagScheduler:
    """Builds a dependency graph from PRD stories and resolves execution order.

    Uses :mod:`graphlib.TopologicalSorter` (stdlib, Python 3.9+) — no extra
    dependencies required.
    """

    def __init__(self, prd: Prd) -> None:
        self._prd = prd

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan(self) -> ExecutionPlan:
        """Return parallelisable waves and the critical path for all stories."""
        story_map = {s.id: s for s in self._prd.user_stories}
        dep_map: dict[str, set[str]] = {
            s.id: set(s.depends_on) for s in self._prd.user_stories
        }

        sorter: graphlib.TopologicalSorter[str] = graphlib.TopologicalSorter(dep_map)
        try:
            sorter.prepare()
        except graphlib.CycleError as exc:
            raise ValueError(f"Dependency cycle detected in PRD: {exc}") from exc

        waves: list[list[Story]] = []
        while sorter.is_active():
            ready_ids = list(sorter.get_ready())
            wave = [story_map[sid] for sid in ready_ids if sid in story_map]
            if wave:
                waves.append(wave)
            for sid in ready_ids:
                sorter.done(sid)

        return ExecutionPlan(waves=waves, critical_path=self._longest_path(dep_map))

    def ready_stories(self, completed: set[str]) -> list[Story]:
        """Return stories whose dependencies are all in *completed*."""
        return self._prd.ready_stories(completed)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _longest_path(self, dep_map: dict[str, set[str]]) -> list[str]:
        """Return the story IDs along the longest dependency chain."""
        memo: dict[str, list[str]] = {}

        def _depth(node: str) -> list[str]:
            if node in memo:
                return memo[node]
            parents = dep_map.get(node, set())
            if not parents:
                result: list[str] = [node]
            else:
                longest_parent = max((_depth(p) for p in parents), key=len)
                result = longest_parent + [node]
            memo[node] = result
            return result

        if not dep_map:
            return []
        return max((_depth(n) for n in dep_map), key=len)

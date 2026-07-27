"""Scenario Matcher: 匹配基线和目标评测中的场景."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from agenteval.infra.models.scenario_execution_model import ScenarioExecutionModel


class ScenarioMatcher:
    """匹配基线和目标评测中的场景.

    按 scenario_id 匹配。仅出现在一侧的标记为 None。
    """

    def match(
        self,
        baseline_execs: list[ScenarioExecutionModel],
        target_execs: list[ScenarioExecutionModel],
    ) -> list[tuple[ScenarioExecutionModel | None, ScenarioExecutionModel | None]]:
        """匹配两个评测的场景执行.

        Args:
            baseline_execs: 基线评测的场景执行列表
            target_execs: 目标评测的场景执行列表

        Returns:
            匹配对列表 [(baseline_exec, target_exec), ...]
            一侧缺失时对应位置为 None
        """
        baseline_map: dict[UUID, ScenarioExecutionModel] = {
            e.scenario_id: e for e in baseline_execs
        }
        target_map: dict[UUID, ScenarioExecutionModel] = {
            e.scenario_id: e for e in target_execs
        }

        all_ids = set(baseline_map.keys()) | set(target_map.keys())
        pairs: list[tuple[ScenarioExecutionModel | None, ScenarioExecutionModel | None]] = []

        for sid in sorted(all_ids, key=str):
            pairs.append((baseline_map.get(sid), target_map.get(sid)))

        return pairs

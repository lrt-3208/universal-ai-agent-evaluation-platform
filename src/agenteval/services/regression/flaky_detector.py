"""Flaky Detector: 检测不稳定场景."""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from agenteval.infra.models.scenario_execution_model import ScenarioExecutionModel


class FlakyDetector:
    """检测不稳定场景：历史评测中得分波动大的场景.

    可选扩展点 (MAY)，MVP 可不实现。
    """

    def __init__(self, threshold_std: float = 0.15):
        """初始化.

        Args:
            threshold_std: 标准差阈值，超过此值标记为 flaky
        """
        self.threshold_std = threshold_std

    def detect(
        self,
        scenario_execs_history: dict[UUID, list[ScenarioExecutionModel]],
    ) -> set[UUID]:
        """检测 flaky 场景.

        Args:
            scenario_execs_history: {scenario_id: [exec_v1, exec_v2, ..., exec_vN]}

        Returns:
            被标记为 flaky 的 scenario_id 集合
        """
        flaky_ids: set[UUID] = set()

        for scenario_id, execs in scenario_execs_history.items():
            scores = [
                e.overall_score
                for e in execs
                if e.overall_score is not None
            ]
            # 至少需要 3 次评测才能判断波动
            if len(scores) < 3:
                continue

            std = statistics.stdev(scores)
            if std > self.threshold_std:
                flaky_ids.add(scenario_id)

        return flaky_ids

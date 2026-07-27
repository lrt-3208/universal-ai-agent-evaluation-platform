"""Metrics Plugin SPI.

Reference: ../docs/phases/phase-7-plugin.md §5.5
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from agenteval.plugins.base import Plugin

if TYPE_CHECKING:
    from agenteval.judges import JudgeContext, MetricScore


@dataclass
class MetricDefinition:
    """指标定义."""

    key: str
    name: str
    description: str
    score_range: tuple[float, float]  # (min, max)
    weight_default: float
    higher_is_better: bool


class MetricsPlugin(Plugin, ABC):
    """Metrics 插件接口：扩展指标计算."""

    @property
    def plugin_type(self) -> str:
        """插件类型."""
        return "metrics"

    @abstractmethod
    def metric_definitions(self) -> list[MetricDefinition]:
        """返回该插件提供的指标定义.

        Returns:
            指标定义列表
        """
        pass

    @abstractmethod
    async def compute(self, metric_key: str, ctx: JudgeContext) -> MetricScore:
        """计算单个指标.

        Args:
            metric_key: 指标 key
            ctx: Judge 上下文

        Returns:
            MetricScore 结果
        """
        pass

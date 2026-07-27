"""Judge SPI — base interfaces, data structures, and registry.

Reference: ../docs/contracts/judge-spi.md §3
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from agenteval.core.llm_client import LLMClient
from agenteval.core.spi import Registry


@dataclass
class MetricScore:
    """Single metric evaluation result."""

    metric_key: str
    metric_name: str
    score: float  # 0.0 ~ 1.0
    weight: float = 1.0
    max_score: float = 1.0
    detail: dict = field(default_factory=dict)
    reasoning: str | None = None


@dataclass
class JudgeContext:
    """Evaluation context passed to each Judge."""

    scenario: Any  # ScenarioModel
    agent_execution: Any  # AgentExecutionModel
    trace: Any | None = None  # TraceModel
    config: dict = field(default_factory=dict)
    llm_client: LLMClient | None = None


@dataclass
class JudgeOutput:
    """Judge evaluation output."""

    judge_type: str
    metric_scores: list[MetricScore] = field(default_factory=list)
    reasoning: str | None = None
    error: str | None = None
    metadata: dict = field(default_factory=dict)


class Judge(ABC):
    """Judge SPI base interface.

    Each Judge evaluates one or more metrics.
    MUST implement: evaluate(), judge_type, supported_metrics
    """

    @abstractmethod
    async def evaluate(self, ctx: JudgeContext) -> JudgeOutput:
        """Execute evaluation, return scored metrics."""
        ...

    @property
    @abstractmethod
    def judge_type(self) -> str:
        """Judge type identifier (e.g., 'rule', 'llm', 'embedding')."""
        ...

    @property
    def supported_metrics(self) -> set[str]:
        """Set of metric keys this Judge can evaluate."""
        return set()

    def validate_config(self, config: dict) -> bool:
        """Validate judge-specific configuration. Default: always valid."""
        return True


class JudgeRegistry(Registry[Judge]):
    """Judge unified registry.

    Usage:
        JudgeRegistry.register("rule", RuleJudge)
        judge = JudgeRegistry.create("rule")
    """

    @classmethod
    def create(cls, name: str, **kwargs) -> Judge:
        """Create Judge instance by type name."""
        if name not in cls._registry:
            from agenteval.core.exceptions import AgentEvalException
            raise AgentEvalException(
                code=40601,
                message=f"Unknown judge type: '{name}'. Available: {list(cls._registry.keys())}",
                http_status=400,
            )
        judge_cls = cls._registry[name]
        return judge_cls(**kwargs)


__all__ = [
    "MetricScore",
    "JudgeContext",
    "JudgeOutput",
    "Judge",
    "JudgeRegistry",
]

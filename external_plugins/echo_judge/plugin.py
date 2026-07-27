"""Echo Judge Plugin — 用于测试的简单 Judge 插件."""

from __future__ import annotations

from agenteval.judges import Judge, JudgeContext, JudgeOutput, MetricScore
from agenteval.plugins.spi import JudgePlugin


class EchoJudge(Judge):
    """返回固定分数的测试 Judge."""

    def __init__(self, fixed_score: float = 0.8):
        """初始化.

        Args:
            fixed_score: 固定分数
        """
        self.fixed_score = fixed_score

    @property
    def judge_type(self) -> str:
        """Judge 类型."""
        return "echo"

    @property
    def supported_metrics(self) -> set[str]:
        """支持的指标."""
        return {"echo_score"}

    async def evaluate(self, ctx: JudgeContext) -> JudgeOutput:
        """评估并返回固定分数."""
        return JudgeOutput(
            judge_type=self.judge_type,
            metric_scores=[
                MetricScore(
                    metric_key="echo_score",
                    metric_name="Echo Score",
                    score=self.fixed_score,
                    weight=1.0,
                    reasoning=f"Echo judge returns fixed score: {self.fixed_score}",
                )
            ],
        )


class EchoJudgePlugin(JudgePlugin):
    """Echo Judge 插件."""

    @property
    def name(self) -> str:
        """插件名称."""
        return "echo_judge"

    @property
    def version(self) -> str:
        """插件版本."""
        return "1.0.0"

    def supported_metrics(self) -> list[str]:
        """支持的指标列表."""
        return ["echo_score"]

    async def initialize(self, config: dict) -> None:
        """初始化插件."""
        self.config = config

    async def teardown(self) -> None:
        """清理资源."""
        pass

    def create_judge(self, config: dict) -> Judge:
        """创建 Judge 实例."""
        fixed_score = config.get("fixed_score", 0.8)
        return EchoJudge(fixed_score=fixed_score)

    def validate_config(self, config: dict) -> list[str]:
        """校验配置."""
        errors = []
        if "fixed_score" in config:
            score = config["fixed_score"]
            if not isinstance(score, (int, float)):
                errors.append("fixed_score must be a number")
            elif not 0 <= score <= 1:
                errors.append("fixed_score must be between 0 and 1")
        return errors

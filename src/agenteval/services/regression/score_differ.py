"""Score Differ: 逐场景/逐指标计算得分差异."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from agenteval.infra.models.scenario_execution_model import ScenarioExecutionModel


class RegressionVerdict(str, Enum):
    """回归判定结果."""

    IMPROVED = "improved"
    REGRESSED = "regressed"
    UNCHANGED = "unchanged"
    FLAKY = "flaky"


@dataclass
class ScenarioDiff:
    """单个场景的差异结果."""

    scenario_id: UUID
    external_id: str
    title: str
    baseline_score: float | None
    target_score: float | None
    score_delta: float | None
    baseline_verdict: str | None
    target_verdict: str | None
    verdict: str  # improved | regressed | unchanged | flaky
    metric_deltas: dict[str, float] = field(default_factory=dict)
    notes: str | None = None

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            "scenario_id": str(self.scenario_id),
            "external_id": self.external_id,
            "title": self.title,
            "baseline_score": self.baseline_score,
            "target_score": self.target_score,
            "score_delta": self.score_delta,
            "baseline_verdict": self.baseline_verdict,
            "target_verdict": self.target_verdict,
            "verdict": self.verdict,
            "metric_deltas": self.metric_deltas,
            "notes": self.notes,
        }


class ScoreDiffer:
    """计算逐场景和逐指标的得分差异.

    基于动态指标集合工作（Open/Closed），新增 Judge 只需注册，ScoreDiffer 不需修改。
    """

    def __init__(self, regression_threshold: float = 0.05):
        """初始化.

        Args:
            regression_threshold: 回归阈值，低于此 delta 视为 unchanged
        """
        self.threshold = regression_threshold

    def diff(
        self,
        pairs: list[tuple[ScenarioExecutionModel | None, ScenarioExecutionModel | None]],
        metrics_filter: list[str] | None = None,
    ) -> list[ScenarioDiff]:
        """计算所有场景对的差异.

        Args:
            pairs: 匹配的场景执行对列表
            metrics_filter: 可选的指标过滤列表

        Returns:
            ScenarioDiff 列表
        """
        diffs = []
        for baseline, target in pairs:
            diff = self._diff_single(baseline, target, metrics_filter)
            diffs.append(diff)
        return diffs

    def _diff_single(
        self,
        baseline: ScenarioExecutionModel | None,
        target: ScenarioExecutionModel | None,
        metrics_filter: list[str] | None,
    ) -> ScenarioDiff:
        """计算单个场景对的差异."""
        baseline_scores = self._extract_metric_scores(baseline, metrics_filter)
        target_scores = self._extract_metric_scores(target, metrics_filter)

        # 计算每个指标的 delta
        metric_deltas: dict[str, float] = {}
        for key in set(baseline_scores.keys()) | set(target_scores.keys()):
            b = baseline_scores.get(key)
            t = target_scores.get(key)
            if b is not None and t is not None:
                metric_deltas[key] = round(t - b, 4)

        # 总体得分
        baseline_overall = baseline.overall_score if baseline else None
        target_overall = target.overall_score if target else None
        score_delta = None
        if baseline_overall is not None and target_overall is not None:
            score_delta = round(target_overall - baseline_overall, 4)

        # 判定
        verdict = self._determine_verdict(score_delta, baseline, target)

        # 获取场景信息
        ref_exec = target or baseline
        # scenario 是通过 regression_service 预加载的属性
        scenario = getattr(ref_exec, "_loaded_scenario", None) if ref_exec else None
        external_id = scenario.external_id if scenario else "unknown"
        title = scenario.title if scenario else "Unknown"

        return ScenarioDiff(
            scenario_id=ref_exec.scenario_id if ref_exec else None,
            external_id=external_id,
            title=title,
            baseline_score=baseline_overall,
            target_score=target_overall,
            score_delta=score_delta,
            baseline_verdict=baseline.overall_verdict if baseline else None,
            target_verdict=target.overall_verdict if target else None,
            verdict=verdict.value,
            metric_deltas=metric_deltas,
            notes=self._generate_notes(baseline, target, verdict, score_delta),
        )

    def _extract_metric_scores(
        self,
        exec_model: ScenarioExecutionModel | None,
        metrics_filter: list[str] | None,
    ) -> dict[str, float]:
        """从场景执行中提取指标得分.

        同一 metric 取最高分（多 Judge 情况）。
        """
        if not exec_model:
            return {}
        # judge_results 是通过 regression_service 预加载的属性
        judge_results = getattr(exec_model, "_loaded_judge_results", None)
        if not judge_results:
            return {}

        scores: dict[str, float] = {}
        for jr in judge_results:
            if jr.status != "completed":
                continue
            # metric_scores 是 JSONB list，每个元素是 dict
            for ms in jr.metric_scores:
                metric_key = ms.get("metric_key", "") if isinstance(ms, dict) else getattr(ms, "metric_key", "")
                score = ms.get("score", 0.0) if isinstance(ms, dict) else getattr(ms, "score", 0.0)
                if metrics_filter and metric_key not in metrics_filter:
                    continue
                # 同 metric 取最高分
                current = scores.get(metric_key)
                if current is None or score > current:
                    scores[metric_key] = score
        return scores

    def _determine_verdict(
        self,
        score_delta: float | None,
        baseline: ScenarioExecutionModel | None,
        target: ScenarioExecutionModel | None,
    ) -> RegressionVerdict:
        """判定回归结果."""
        # 一侧缺失
        if baseline is None and target is not None:
            return RegressionVerdict.IMPROVED  # 新增场景覆盖
        if baseline is not None and target is None:
            return RegressionVerdict.REGRESSED  # 场景丢失

        if score_delta is None:
            return RegressionVerdict.UNCHANGED

        if abs(score_delta) < self.threshold:
            return RegressionVerdict.UNCHANGED
        elif score_delta > 0:
            return RegressionVerdict.IMPROVED
        else:
            return RegressionVerdict.REGRESSED

    def _generate_notes(
        self,
        baseline: ScenarioExecutionModel | None,
        target: ScenarioExecutionModel | None,
        verdict: RegressionVerdict,
        score_delta: float | None,
    ) -> str:
        """生成备注信息."""
        if baseline is None:
            return "New scenario in target evaluation"
        if target is None:
            return "Scenario missing in target evaluation"
        if verdict == RegressionVerdict.REGRESSED and score_delta is not None:
            return f"Score dropped by {abs(score_delta):.4f}"
        elif verdict == RegressionVerdict.IMPROVED and score_delta is not None:
            return f"Score improved by {score_delta:.4f}"
        return "No significant change"

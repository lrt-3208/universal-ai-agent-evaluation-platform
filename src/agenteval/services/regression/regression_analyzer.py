"""Regression Analyzer: 分析回归趋势和风险等级."""

from __future__ import annotations

from dataclasses import dataclass, field

from agenteval.services.regression.score_differ import RegressionVerdict, ScenarioDiff


@dataclass
class RegressionAnalysis:
    """回归分析结果."""

    overall_verdict: str
    summary: dict
    metric_diffs: dict
    scenario_diffs: list[ScenarioDiff] = field(default_factory=list)


class RegressionAnalyzer:
    """分析回归趋势和风险等级."""

    def analyze(
        self,
        scenario_diffs: list[ScenarioDiff],
        metric_diffs: dict,
    ) -> RegressionAnalysis:
        """分析回归结果.

        Args:
            scenario_diffs: 场景差异列表
            metric_diffs: 指标级差异

        Returns:
            RegressionAnalysis 结果
        """
        improved = sum(1 for d in scenario_diffs if d.verdict == RegressionVerdict.IMPROVED.value)
        regressed = sum(1 for d in scenario_diffs if d.verdict == RegressionVerdict.REGRESSED.value)
        unchanged = sum(1 for d in scenario_diffs if d.verdict == RegressionVerdict.UNCHANGED.value)
        flaky = sum(1 for d in scenario_diffs if d.verdict == RegressionVerdict.FLAKY.value)

        total = len(scenario_diffs)
        regression_rate = regressed / total if total > 0 else 0.0

        # 风险等级
        risk = self._assess_risk(regression_rate)

        # 总体结论
        if regressed > improved:
            overall = RegressionVerdict.REGRESSED.value
        elif improved > regressed:
            overall = RegressionVerdict.IMPROVED.value
        else:
            overall = RegressionVerdict.UNCHANGED.value

        summary = {
            "total_compared": total,
            "improved": improved,
            "regressed": regressed,
            "unchanged": unchanged,
            "flaky": flaky,
            "regression_rate": round(regression_rate, 4),
            "regression_risk": risk,
        }

        return RegressionAnalysis(
            overall_verdict=overall,
            summary=summary,
            metric_diffs=metric_diffs,
            scenario_diffs=scenario_diffs,
        )

    def _assess_risk(self, regression_rate: float) -> str:
        """评估风险等级.

        Args:
            regression_rate: 回归率 (0.0 - 1.0)

        Returns:
            风险等级: low | medium | high | critical
        """
        if regression_rate >= 0.2:
            return "critical"
        elif regression_rate >= 0.1:
            return "high"
        elif regression_rate >= 0.05:
            return "medium"
        else:
            return "low"

    def compute_metric_diffs(self, scenario_diffs: list[ScenarioDiff]) -> dict:
        """计算指标级聚合差异.

        Args:
            scenario_diffs: 场景差异列表

        Returns:
            指标级差异字典
        """
        metric_deltas: dict[str, list[float]] = {}
        for diff in scenario_diffs:
            for key, delta in diff.metric_deltas.items():
                metric_deltas.setdefault(key, []).append(delta)

        result = {}
        for key, deltas in metric_deltas.items():
            mean_delta = sum(deltas) / len(deltas) if deltas else 0.0
            result[key] = {
                "baseline_mean": None,  # 由调用方填充
                "target_mean": None,
                "delta": round(mean_delta, 4),
                "direction": "improved" if mean_delta > 0 else "regressed" if mean_delta < 0 else "unchanged",
                "affected_count": len(deltas),
            }
        return result

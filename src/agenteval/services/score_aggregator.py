"""Score Aggregator — weighted aggregation of multi-Judge results.

Reference: ../docs/phases/phase-4-judge.md §8
Implements: weighted average + verdict threshold logic.
Open/Closed: new Judges/metrics don't require modifying this class.
"""

from dataclasses import dataclass, field

from agenteval.judges import JudgeOutput, MetricScore


@dataclass
class AggregatedScore:
    """Aggregation result."""

    overall_score: float
    overall_verdict: str  # "pass" | "partial" | "fail"
    metric_scores: list[MetricScore] = field(default_factory=list)
    metric_details: dict = field(default_factory=dict)  # key → aggregated score


class ScoreAggregator:
    """Multi-Judge result weighted aggregation.

    Rules:
    1. Same metric_key from multiple Judges → weighted average
    2. overall_score = sum(metric_score * metric_weight) / sum(metric_weight)
    3. Verdict thresholds:
       - overall_score >= 0.8 → "pass"
       - overall_score >= 0.5 → "partial"
       - overall_score < 0.5 → "fail"
    """

    def __init__(self, pass_threshold: float = 0.8, partial_threshold: float = 0.5):
        self.pass_threshold = pass_threshold
        self.partial_threshold = partial_threshold

    def aggregate(
        self,
        judge_outputs: list[JudgeOutput],
        weights: dict[str, float] | None = None,
    ) -> AggregatedScore:
        """Aggregate all Judge outputs into a single score + verdict.

        Args:
            judge_outputs: List of JudgeOutput from different Judges
            weights: Optional global weight overrides per metric_key

        Returns:
            AggregatedScore with overall_score, verdict, and details
        """
        weights = weights or {}
        # Collect: metric_key → [(score, weight)]
        metric_map: dict[str, list[tuple[float, float]]] = {}

        for output in judge_outputs:
            if output.error:
                continue  # Skip failed judges
            for ms in output.metric_scores:
                weight = ms.weight if ms.weight else weights.get(ms.metric_key, 1.0)
                metric_map.setdefault(ms.metric_key, []).append((ms.score, weight))

        if not metric_map:
            return AggregatedScore(
                overall_score=0.0,
                overall_verdict="fail",
                metric_scores=[],
            )

        # Per-metric weighted average
        metric_aggregated: dict[str, float] = {}
        metric_weight_map: dict[str, float] = {}
        all_metric_scores: list[MetricScore] = []

        for key, scores_weights in metric_map.items():
            total_w = sum(w for _, w in scores_weights)
            weighted_sum = sum(s * w for s, w in scores_weights)
            avg_score = weighted_sum / total_w if total_w > 0 else 0.0
            metric_aggregated[key] = round(avg_score, 4)
            metric_weight_map[key] = weights.get(key, 1.0)

            # Keep the first MetricScore as representative (with aggregated score)
            representative = None
            for output in judge_outputs:
                for ms in output.metric_scores:
                    if ms.metric_key == key:
                        representative = ms
                        break
                if representative:
                    break

            if representative:
                all_metric_scores.append(MetricScore(
                    metric_key=key,
                    metric_name=representative.metric_name,
                    score=metric_aggregated[key],
                    weight=metric_weight_map[key],
                    detail=representative.detail,
                    reasoning=representative.reasoning,
                ))

        # Global weighted average
        total_weight = sum(metric_weight_map.values())
        if total_weight > 0:
            overall = sum(
                score * metric_weight_map[key]
                for key, score in metric_aggregated.items()
            ) / total_weight
        else:
            overall = 0.0

        overall = round(max(0.0, min(1.0, overall)), 4)

        # Verdict
        if overall >= self.pass_threshold:
            verdict = "pass"
        elif overall >= self.partial_threshold:
            verdict = "partial"
        else:
            verdict = "fail"

        return AggregatedScore(
            overall_score=overall,
            overall_verdict=verdict,
            metric_scores=all_metric_scores,
            metric_details=metric_aggregated,
        )

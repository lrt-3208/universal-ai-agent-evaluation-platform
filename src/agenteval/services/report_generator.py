"""Report Generator — JSON + HTML report generation.

Reference: ../docs/phases/phase-5-report.md §5.2
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import structlog

from agenteval.schemas.report import (
    EvaluationSummary,
    MetricsSnapshot,
    ReportData,
    ReportSummary,
    ScenarioResultItem,
    TraceHighlight,
)

logger = structlog.get_logger()


class ReportGenerator:
    """Generate evaluation reports in JSON/HTML format."""

    async def collect_data(self, session, evaluation_id: uuid.UUID) -> ReportData:
        """Collect all data needed for report."""
        from agenteval.infra.repositories.dataset_repo import DatasetRepository
        from agenteval.infra.repositories.evaluation_repo import EvaluationRepository
        from agenteval.infra.repositories.execution_repo import (
            AgentExecutionRepository,
            ScenarioExecutionRepository,
            TraceRepository,
        )
        from agenteval.infra.repositories.judge_result_repo import JudgeResultRepository
        from agenteval.infra.repositories.scenario_repo import ScenarioRepository

        eval_repo = EvaluationRepository(session)
        evaluation = await eval_repo.get_by_id(evaluation_id)
        if not evaluation:
            raise ValueError(f"Evaluation not found: {evaluation_id}")

        # Get dataset info
        dataset_repo = DatasetRepository(session)
        dataset = await dataset_repo.get_by_id(evaluation.dataset_id)
        dataset_name = dataset.name if dataset else "Unknown"
        dataset_version = dataset.version if dataset else "1.0"

        # Get executions
        exec_repo = ScenarioExecutionRepository(session)
        executions = await exec_repo.list_by_evaluation(evaluation_id)

        # Build evaluation summary
        duration = 0
        if evaluation.started_at and evaluation.completed_at:
            duration = int((evaluation.completed_at - evaluation.started_at).total_seconds())

        eval_summary = EvaluationSummary(
            id=evaluation.id,
            name=evaluation.name,
            version_label=evaluation.version_label,
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            agent_config=evaluation.agent_config,
            status=evaluation.status,
            started_at=evaluation.started_at,
            completed_at=evaluation.completed_at,
            duration_seconds=duration,
        )

        # Load related data for each execution
        scenario_repo = ScenarioRepository(session)
        ae_repo = AgentExecutionRepository(session)
        judge_repo = JudgeResultRepository(session)
        trace_repo = TraceRepository(session)

        scenario_results = []
        latencies = []
        costs = []
        all_metric_scores: dict[str, list[float]] = {}
        trace_highlights = []

        for exec_record in executions:
            # Load scenario
            scenario = await scenario_repo.get_by_id(exec_record.scenario_id)
            external_id = scenario.external_id if scenario else ""
            title = scenario.title if scenario else ""
            tags = scenario.tags if scenario else []

            # Load agent execution
            ae = await ae_repo.get_by_scenario_execution(exec_record.id)
            latency_ms = ae.latency_ms if ae else None
            cost_usd = ae.cost_usd if ae else None

            if latency_ms:
                latencies.append(latency_ms)
            if cost_usd:
                costs.append(cost_usd)

            # Load judge results
            judge_results = await judge_repo.list_by_scenario_execution(exec_record.id)
            metric_scores: dict[str, float] = {}
            for jr in judge_results:
                for ms in jr.metric_scores:
                    key = ms.get("metric_key", "")
                    score = ms.get("score", 0.0)
                    if key:
                        metric_scores[key] = score
                        all_metric_scores.setdefault(key, []).append(score)

            scenario_results.append(ScenarioResultItem(
                scenario_id=exec_record.scenario_id,
                external_id=external_id,
                title=title,
                status=exec_record.status,
                overall_score=exec_record.overall_score,
                overall_verdict=exec_record.overall_verdict,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                metric_scores=metric_scores,
                tags=tags,
                error_message=exec_record.error_message,
            ))

            # Collect trace highlights
            if ae and ae.trace_id:
                trace = await trace_repo.get_by_id(ae.trace_id)
                if trace:
                    highlights = self._extract_trace_highlights(trace.span_tree, external_id)
                    trace_highlights.extend(highlights)

        # Build metrics snapshot
        metrics = self._compute_metrics(executions, scenario_results, latencies, costs, all_metric_scores)

        # Build summary
        summary = self._build_summary(metrics, scenario_results, duration)

        return ReportData(
            evaluation=eval_summary,
            metrics=metrics,
            scenario_results=scenario_results,
            trace_highlights=trace_highlights[:10],  # Limit highlights
            summary=summary,
        )

    def _compute_metrics(
        self,
        executions,
        results: list[ScenarioResultItem],
        latencies: list[int],
        costs: list[float],
        metric_scores: dict[str, list[float]],
    ) -> MetricsSnapshot:
        """Compute metrics snapshot."""
        scored = [r for r in results if r.overall_score is not None]
        scores = [r.overall_score for r in scored if r.overall_score is not None]
        pass_count = len([s for s in scores if s >= 0.8])

        # Aggregate metrics
        metric_aggregates = {}
        for key, values in metric_scores.items():
            if values:
                metric_aggregates[key] = {
                    "mean": round(sum(values) / len(values), 4),
                    "min": round(min(values), 4),
                    "max": round(max(values), 4),
                    "p50": round(self._percentile(values, 50), 4),
                    "p95": round(self._percentile(values, 95), 4),
                }

        return MetricsSnapshot(
            scenario_count=len(executions),
            executed_count=len([e for e in executions if e.status == "completed"]),
            scored_count=len(scored),
            pass_rate=pass_count / len(scores) if scores else 0.0,
            metric_aggregates=metric_aggregates,
            cost_total_usd=sum(costs) if costs else 0.0,
            latency_avg_ms=sum(latencies) / len(latencies) if latencies else 0.0,
            latency_p50_ms=self._percentile(latencies, 50),
            latency_p95_ms=self._percentile(latencies, 95),
            latency_p99_ms=self._percentile(latencies, 99),
        )

    def _build_summary(
        self,
        metrics: MetricsSnapshot,
        results: list[ScenarioResultItem],
        duration_seconds: int,
    ) -> ReportSummary:
        """Build report summary with key findings."""
        failed = [r for r in results if r.overall_verdict in ("fail", None) and r.status == "completed"]

        # Find top failed metrics
        metric_fails: dict[str, int] = {}
        for r in results:
            if r.overall_verdict in ("fail", "partial"):
                for key, score in r.metric_scores.items():
                    if score < 0.5:
                        metric_fails[key] = metric_fails.get(key, 0) + 1

        top_failed = sorted(metric_fails.items(), key=lambda x: -x[1])[:5]
        top_failed_list = [{"metric": k, "fail_count": v} for k, v in top_failed]

        # Generate findings
        findings = self._generate_findings(metrics, results)

        overall_score = metrics.metric_aggregates.get("correctness", {}).get("mean", 0.0)

        return ReportSummary(
            total_scenarios=metrics.scenario_count,
            pass_rate=metrics.pass_rate,
            overall_score=overall_score,
            failed_scenarios=len(failed),
            top_failed_metrics=top_failed_list,
            cost_total_usd=metrics.cost_total_usd,
            duration_seconds=duration_seconds,
            key_findings=findings,
        )

    def _generate_findings(self, metrics: MetricsSnapshot, results: list[ScenarioResultItem]) -> list[str]:
        """Generate key findings."""
        findings = []

        if metrics.pass_rate >= 0.9:
            findings.append(f"Pass rate {metrics.pass_rate:.1%} — 整体表现优秀")
        elif metrics.pass_rate >= 0.7:
            findings.append(f"Pass rate {metrics.pass_rate:.1%} — 存在改进空间")
        else:
            findings.append(f"Pass rate {metrics.pass_rate:.1%} — 需要重点关注")

        for metric, agg in metrics.metric_aggregates.items():
            if agg.get("mean", 1.0) < 0.5:
                findings.append(f"指标 '{metric}' 均分 {agg['mean']:.2f}，低于 0.5，需要优先改进")

        slow = [r for r in results if r.latency_ms and r.latency_ms > metrics.latency_p95_ms]
        if slow and metrics.latency_p95_ms > 0:
            findings.append(f"{len(slow)} 个场景延迟超过 P95 ({metrics.latency_p95_ms:.0f}ms)")

        return findings

    def _extract_trace_highlights(self, span_tree: dict, external_id: str) -> list[TraceHighlight]:
        """Extract trace highlights (slowest LLM, failed tools)."""
        highlights = []
        if not span_tree:
            return highlights

        # Find slowest LLM call
        llm_spans = self._flatten_by_type(span_tree, "llm_call")
        if llm_spans:
            slowest = max(llm_spans, key=lambda s: s.get("duration_ms", 0))
            highlights.append(TraceHighlight(
                scenario_external_id=external_id,
                span_type="llm_call",
                span_name=slowest.get("name", ""),
                duration_ms=slowest.get("duration_ms", 0),
                status=slowest.get("status", "ok"),
                detail=f"Slowest LLM call in {external_id}",
            ))

        # Find failed tool calls
        tool_spans = self._flatten_by_type(span_tree, "tool_call")
        for ts in tool_spans:
            if ts.get("status") == "error":
                highlights.append(TraceHighlight(
                    scenario_external_id=external_id,
                    span_type="tool_call",
                    span_name=ts.get("name", ""),
                    duration_ms=ts.get("duration_ms", 0),
                    status=ts.get("status", "error"),
                    detail=f"Failed tool call: {ts.get('input_data', {}).get('tool_name', 'unknown')}",
                ))

        return highlights

    def _flatten_by_type(self, span: dict, span_type: str) -> list[dict]:
        """Flatten spans of a specific type."""
        result = []
        if span.get("span_type") == span_type:
            result.append(span)
        for child in span.get("children", []):
            result.extend(self._flatten_by_type(child, span_type))
        return result

    def _percentile(self, values: list[float], p: int) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        k = (len(sorted_vals) - 1) * p / 100
        f = int(k)
        c = min(f + 1, len(sorted_vals) - 1)
        return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)

    def generate_json(self, data: ReportData) -> bytes:
        """Generate JSON report content."""
        return json.dumps(
            data.model_dump(),
            default=str,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")

    def generate_html(self, data: ReportData) -> bytes:
        """Generate HTML report content."""
        html = self._render_html_template(data)
        return html.encode("utf-8")

    def _render_html_template(self, data: ReportData) -> str:
        """Render HTML report using inline template."""
        d = data.model_dump()
        eval_info = d["evaluation"]
        metrics = d["metrics"]
        summary = d["summary"]
        results = d["scenario_results"]
        highlights = d["trace_highlights"]

        # Build metric rows
        metric_rows = ""
        for metric, agg in metrics.get("metric_aggregates", {}).items():
            metric_rows += f"""
            <tr>
                <td>{metric}</td>
                <td>{agg.get('mean', 0):.4f}</td>
                <td>{agg.get('min', 0):.4f}</td>
                <td>{agg.get('max', 0):.4f}</td>
                <td>{agg.get('p50', 0):.4f}</td>
                <td>{agg.get('p95', 0):.4f}</td>
            </tr>"""

        # Build scenario rows
        scenario_rows = ""
        for r in results:
            score_str = f"{r['overall_score']:.2f}" if r.get("overall_score") else "N/A"
            verdict = r.get("overall_verdict") or "N/A"
            verdict_class = verdict if verdict in ("pass", "partial", "fail") else ""
            latency = r.get("latency_ms") or "-"
            cost = f"{r['cost_usd']:.4f}" if r.get("cost_usd") else "-"
            scenario_rows += f"""
            <tr>
                <td>{r.get('external_id', '')}</td>
                <td>{r.get('title', '')}</td>
                <td>{r.get('status', '')}</td>
                <td>{score_str}</td>
                <td class="{verdict_class}">{verdict}</td>
                <td>{latency}</td>
                <td>{cost}</td>
            </tr>"""

        # Build findings list
        findings_html = ""
        for finding in summary.get("key_findings", []):
            findings_html += f"<li>{finding}</li>"

        # Build highlight rows
        highlight_rows = ""
        for h in highlights:
            highlight_rows += f"""
            <tr>
                <td>{h.get('scenario_external_id', '')}</td>
                <td>{h.get('span_type', '')}</td>
                <td>{h.get('span_name', '')}</td>
                <td>{h.get('duration_ms', 0)}</td>
                <td class="{h.get('status', '')}">{h.get('status', '')}</td>
                <td>{h.get('detail', '')}</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>评测报告 - {eval_info.get('name', '')}</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4caf50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 20px 0; }}
        .metric-card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; text-align: center; }}
        .metric-card h4 {{ margin: 0 0 8px 0; color: #666; font-size: 14px; }}
        .metric-card .big-number {{ font-size: 28px; font-weight: bold; color: #333; margin: 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f8f8; font-weight: 600; }}
        .pass {{ color: #4caf50; font-weight: bold; }}
        .partial {{ color: #ff9800; font-weight: bold; }}
        .fail {{ color: #f44336; font-weight: bold; }}
        .error {{ color: #f44336; }}
        .ok {{ color: #4caf50; }}
        ul {{ line-height: 1.8; }}
        .meta {{ color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>评测报告</h1>
        <h2>{eval_info.get('name', '')}</h2>
        <p class="meta">版本: {eval_info.get('version_label') or '未标注'}</p>
        <p class="meta">数据集: {eval_info.get('dataset_name', '')} v{eval_info.get('dataset_version', '')}</p>
        <p class="meta">执行时间: {eval_info.get('started_at', '')} ~ {eval_info.get('completed_at', '')}</p>

        <h2>摘要</h2>
        <div class="summary-grid">
            <div class="metric-card">
                <h4>通过率</h4>
                <p class="big-number">{summary.get('pass_rate', 0):.1%}</p>
            </div>
            <div class="metric-card">
                <h4>场景总数</h4>
                <p class="big-number">{summary.get('total_scenarios', 0)}</p>
            </div>
            <div class="metric-card">
                <h4>失败数</h4>
                <p class="big-number">{summary.get('failed_scenarios', 0)}</p>
            </div>
            <div class="metric-card">
                <h4>总花费</h4>
                <p class="big-number">${summary.get('cost_total_usd', 0):.2f}</p>
            </div>
        </div>

        <h2>关键发现</h2>
        <ul>{findings_html}</ul>

        <h2>指标分布</h2>
        <table>
            <tr><th>指标</th><th>均值</th><th>最小</th><th>最大</th><th>P50</th><th>P95</th></tr>
            {metric_rows}
        </table>

        <h2>场景明细</h2>
        <table>
            <tr><th>ID</th><th>标题</th><th>状态</th><th>得分</th><th>判定</th><th>延迟(ms)</th><th>花费($)</th></tr>
            {scenario_rows}
        </table>

        <h2>Trace 高亮</h2>
        <table>
            <tr><th>场景</th><th>类型</th><th>名称</th><th>耗时(ms)</th><th>状态</th><th>说明</th></tr>
            {highlight_rows}
        </table>
    </div>
</body>
</html>"""

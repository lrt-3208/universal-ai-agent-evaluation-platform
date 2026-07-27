"""Diff Report Generator — 回归对比报告生成.

Reference: ../docs/phases/phase-6-regression.md §8
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class RegressionReportData:
    """回归报告数据."""

    regression_id: UUID
    name: str
    baseline_name: str
    target_name: str
    baseline_version: str | None
    target_version: str | None
    created_at: datetime
    summary: dict
    metric_diffs: dict
    scenario_diffs: list[dict]
    top_regressions: list[dict] = field(default_factory=list)
    top_improvements: list[dict] = field(default_factory=list)


class DiffReportGenerator:
    """生成回归对比报告（JSON/HTML）."""

    def generate_json(self, data: RegressionReportData) -> bytes:
        """生成 JSON 格式报告."""
        report = {
            "regression": {
                "id": str(data.regression_id),
                "name": data.name,
                "baseline_name": data.baseline_name,
                "target_name": data.target_name,
                "baseline_version": data.baseline_version,
                "target_version": data.target_version,
                "created_at": data.created_at.isoformat(),
            },
            "summary": data.summary,
            "metric_diffs": data.metric_diffs,
            "scenario_diffs": data.scenario_diffs,
            "top_regressions": data.top_regressions,
            "top_improvements": data.top_improvements,
        }
        return json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")

    def generate_html(self, data: RegressionReportData) -> bytes:
        """生成 HTML 格式报告."""
        html = self._render_html(data)
        return html.encode("utf-8")

    def _render_html(self, data: RegressionReportData) -> str:
        """渲染 HTML 报告."""
        summary = data.summary

        # 构建指标差异行
        metric_rows = ""
        for metric, diff in data.metric_diffs.items():
            delta = diff.get("delta", 0)
            delta_class = "delta-positive" if delta > 0 else "delta-negative" if delta < 0 else ""
            baseline_mean = diff.get("baseline_mean")
            target_mean = diff.get("target_mean")
            metric_rows += f"""
            <tr>
                <td>{metric}</td>
                <td>{f'{baseline_mean:.4f}' if baseline_mean is not None else '-'}</td>
                <td>{f'{target_mean:.4f}' if target_mean is not None else '-'}</td>
                <td class="{delta_class}">{delta:+.4f}</td>
                <td>{diff.get('direction', 'unchanged')}</td>
                <td>{diff.get('affected_count', 0)}</td>
            </tr>"""

        # 构建 Top 回归行
        regression_rows = ""
        for d in data.top_regressions:
            regression_rows += self._render_scenario_row(d, "delta-negative")

        # 构建 Top 改进行
        improvement_rows = ""
        for d in data.top_improvements:
            improvement_rows += self._render_scenario_row(d, "delta-positive")

        # 构建全量场景行
        all_scenario_rows = ""
        for d in data.scenario_diffs:
            delta = d.get("score_delta")
            delta_class = ""
            if delta is not None:
                delta_class = "delta-positive" if delta > 0 else "delta-negative" if delta < 0 else ""
            all_scenario_rows += f"""
            <tr>
                <td>{d.get('external_id', '')}</td>
                <td>{d.get('title', '')}</td>
                <td>{f"{d['baseline_score']:.4f}" if d.get('baseline_score') is not None else '-'}</td>
                <td>{f"{d['target_score']:.4f}" if d.get('target_score') is not None else '-'}</td>
                <td class="{delta_class}">{f"{delta:+.4f}" if delta is not None else '-'}</td>
                <td class="verdict-{d.get('verdict', 'unchanged')}">{d.get('verdict', 'unchanged')}</td>
                <td>{d.get('notes', '')}</td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>回归分析报告 - {data.name}</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #2196f3; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .verdict-improved {{ color: #2e7d32; }}
        .verdict-regressed {{ color: #c62828; font-weight: bold; }}
        .verdict-unchanged {{ color: #757575; }}
        .verdict-flaky {{ color: #f57f17; }}
        .delta-positive {{ color: #2e7d32; }}
        .delta-negative {{ color: #c62828; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin: 20px 0; }}
        .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; text-align: center; }}
        .card h4 {{ margin: 0 0 8px 0; color: #666; font-size: 14px; }}
        .card .big-number {{ font-size: 28px; font-weight: bold; color: #333; margin: 0; }}
        .risk-low {{ color: #4caf50; }}
        .risk-medium {{ color: #ff9800; }}
        .risk-high {{ color: #f44336; }}
        .risk-critical {{ color: #b71c1c; font-weight: bold; }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
        th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f8f8; font-weight: 600; }}
        .meta {{ color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>回归分析报告</h1>
        <h2>{data.name}</h2>
        <p class="meta">基线: {data.baseline_name} ({data.baseline_version or '-'})</p>
        <p class="meta">目标: {data.target_name} ({data.target_version or '-'})</p>
        <p class="meta">生成时间: {data.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h2>摘要</h2>
        <div class="summary-grid">
            <div class="card">
                <h4>总对比数</h4>
                <p class="big-number">{summary.get('total_compared', 0)}</p>
            </div>
            <div class="card verdict-improved">
                <h4>改进</h4>
                <p class="big-number">{summary.get('improved', 0)}</p>
            </div>
            <div class="card verdict-regressed">
                <h4>回归</h4>
                <p class="big-number">{summary.get('regressed', 0)}</p>
            </div>
            <div class="card verdict-unchanged">
                <h4>不变</h4>
                <p class="big-number">{summary.get('unchanged', 0)}</p>
            </div>
            <div class="card verdict-flaky">
                <h4>不稳定</h4>
                <p class="big-number">{summary.get('flaky', 0)}</p>
            </div>
        </div>

        <p>风险等级: <span class="risk-{summary.get('regression_risk', 'low')}">{summary.get('regression_risk', 'low').upper()}</span></p>
        <p>回归率: {summary.get('regression_rate', 0):.2%}</p>

        <h2>指标差异</h2>
        <table>
            <tr><th>指标</th><th>基线均值</th><th>目标均值</th><th>差异</th><th>方向</th><th>影响场景数</th></tr>
            {metric_rows}
        </table>

        <h2>Top 回归场景</h2>
        <table>
            <tr><th>ID</th><th>标题</th><th>基线</th><th>目标</th><th>差异</th><th>判定</th></tr>
            {regression_rows if regression_rows else '<tr><td colspan="6">无回归场景</td></tr>'}
        </table>

        <h2>Top 改进场景</h2>
        <table>
            <tr><th>ID</th><th>标题</th><th>基线</th><th>目标</th><th>差异</th><th>判定</th></tr>
            {improvement_rows if improvement_rows else '<tr><td colspan="6">无改进场景</td></tr>'}
        </table>

        <h2>全量场景对比</h2>
        <table>
            <tr><th>ID</th><th>标题</th><th>基线</th><th>目标</th><th>差异</th><th>判定</th><th>备注</th></tr>
            {all_scenario_rows}
        </table>
    </div>
</body>
</html>"""

    def _render_scenario_row(self, d: dict, delta_class: str) -> str:
        """渲染单个场景行."""
        delta = d.get("score_delta")
        return f"""
            <tr>
                <td>{d.get('external_id', '')}</td>
                <td>{d.get('title', '')}</td>
                <td>{f"{d['baseline_score']:.4f}" if d.get('baseline_score') is not None else '-'}</td>
                <td>{f"{d['target_score']:.4f}" if d.get('target_score') is not None else '-'}</td>
                <td class="{delta_class}">{f"{delta:+.4f}" if delta is not None else '-'}</td>
                <td class="verdict-{d.get('verdict', 'unchanged')}">{d.get('verdict', 'unchanged')}</td>
            </tr>"""

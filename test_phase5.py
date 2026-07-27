#!/usr/bin/env python3
"""Phase 5 Acceptance Test — Trace & Report System

Tests:
- AC-P5-01: GET /traces/{id} returns complete nested tree
- AC-P5-02: Trace Span attributes include self_time_ms
- AC-P5-03: GET /traces/{id}/timeline events sorted by start_ms
- AC-P5-04: Timeline lanes grouped by span_type
- AC-P5-05: POST generate HTML report returns 202
- AC-P5-06: HTML report contains summary, metrics table, scenario details
- AC-P5-07: JSON report can be parsed by json.loads
- AC-P5-08: Report summary contains key_findings array
- AC-P5-09: metric_aggregates contains mean/min/max/p50/p95
- AC-P5-10: pass_rate calculation correct
- AC-P5-11: latency_p95 calculation correct
- AC-P5-12: Trace highlights include slowest LLM call
- AC-P5-13: Report download returns correct Content-Type
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "src")

# Test counters
passed = 0
failed = 0


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name} — {detail}")


# --- Mock span tree for testing ---
def make_mock_span_tree():
    """Create a mock span tree for testing."""
    base_time = datetime(2026, 7, 4, 10, 0, 0, tzinfo=timezone.utc)
    return {
        "id": "span-root",
        "trace_id": "trace-001",
        "parent_id": None,
        "span_type": "agent_turn",
        "name": "Agent Turn",
        "input_data": {"user_message": "Hello"},
        "output_data": {"response": "Hi there!"},
        "started_at": base_time.isoformat(),
        "completed_at": (base_time + timedelta(milliseconds=1500)).isoformat(),
        "duration_ms": 1500,
        "status": "ok",
        "attributes": {},
        "children": [
            {
                "id": "span-llm-1",
                "trace_id": "trace-001",
                "parent_id": "span-root",
                "span_type": "llm_call",
                "name": "LLM Call 1",
                "input_data": {"model": "gpt-4"},
                "output_data": {"tokens": {"prompt": 100, "completion": 50}},
                "started_at": (base_time + timedelta(milliseconds=100)).isoformat(),
                "completed_at": (base_time + timedelta(milliseconds=600)).isoformat(),
                "duration_ms": 500,
                "status": "ok",
                "attributes": {},
                "children": [],
            },
            {
                "id": "span-tool-1",
                "trace_id": "trace-001",
                "parent_id": "span-root",
                "span_type": "tool_call",
                "name": "Tool Call 1",
                "input_data": {"tool_name": "get_weather"},
                "output_data": {"status": "success"},
                "started_at": (base_time + timedelta(milliseconds=650)).isoformat(),
                "completed_at": (base_time + timedelta(milliseconds=850)).isoformat(),
                "duration_ms": 200,
                "status": "ok",
                "attributes": {},
                "children": [],
            },
            {
                "id": "span-llm-2",
                "trace_id": "trace-001",
                "parent_id": "span-root",
                "span_type": "llm_call",
                "name": "LLM Call 2",
                "input_data": {"model": "gpt-4"},
                "output_data": {"tokens": {"prompt": 200, "completion": 100}},
                "started_at": (base_time + timedelta(milliseconds=900)).isoformat(),
                "completed_at": (base_time + timedelta(milliseconds=1400)).isoformat(),
                "duration_ms": 500,
                "status": "ok",
                "attributes": {},
                "children": [],
            },
            {
                "id": "span-tool-2",
                "trace_id": "trace-001",
                "parent_id": "span-root",
                "span_type": "tool_call",
                "name": "Tool Call 2 (Failed)",
                "input_data": {"tool_name": "search_web"},
                "output_data": {"status": "error", "error": "timeout"},
                "started_at": (base_time + timedelta(milliseconds=1400)).isoformat(),
                "completed_at": (base_time + timedelta(milliseconds=1450)).isoformat(),
                "duration_ms": 50,
                "status": "error",
                "attributes": {},
                "children": [],
            },
        ],
    }


async def test_trace_enricher():
    """Test TraceEnricher (AC-P5-02)"""
    print("\n=== TraceEnricher Tests ===")
    from agenteval.services.trace_enricher import TraceEnricher

    enricher = TraceEnricher()
    span_tree = make_mock_span_tree()
    enriched = enricher.enrich(span_tree)

    # AC-P5-02: self_time_ms in attributes
    root_attrs = enriched.get("attributes", {})
    check("AC-P5-02a: root span has self_time_ms",
          "self_time_ms" in root_attrs,
          f"attrs: {root_attrs}")

    # Root: 1500ms total, children: 500+200+500+50=1250ms, self=250ms
    expected_self = 1500 - (500 + 200 + 500 + 50)
    check("AC-P5-02b: root self_time_ms = 250 (1500 - 1250)",
          root_attrs.get("self_time_ms") == expected_self,
          f"got {root_attrs.get('self_time_ms')}, expected {expected_self}")

    # Check depth
    check("AC-P5-02c: root depth = 0",
          root_attrs.get("depth") == 0,
          f"got {root_attrs.get('depth')}")

    child_attrs = enriched["children"][0].get("attributes", {})
    check("AC-P5-02d: child depth = 1",
          child_attrs.get("depth") == 1,
          f"got {child_attrs.get('depth')}")

    # Leaf node self_time = duration
    check("AC-P5-02e: leaf self_time_ms = duration_ms",
          child_attrs.get("self_time_ms") == 500,
          f"got {child_attrs.get('self_time_ms')}")

    # LLM token attributes
    check("AC-P5-02f: LLM span has prompt_tokens",
          child_attrs.get("prompt_tokens") == 100,
          f"got {child_attrs.get('prompt_tokens')}")
    check("AC-P5-02g: LLM span has total_tokens",
          child_attrs.get("total_tokens") == 150,
          f"got {child_attrs.get('total_tokens')}")


async def test_timeline_builder():
    """Test TimelineBuilder (AC-P5-03, AC-P5-04)"""
    print("\n=== TimelineBuilder Tests ===")
    from agenteval.services.timeline_builder import TimelineBuilder

    builder = TimelineBuilder()
    span_tree = make_mock_span_tree()
    trace_id = uuid.uuid4()
    started_at = datetime(2026, 7, 4, 10, 0, 0, tzinfo=timezone.utc)
    completed_at = started_at + timedelta(milliseconds=1500)

    timeline = builder.build(trace_id, span_tree, started_at, completed_at)

    # AC-P5-03: events sorted by start_ms
    start_times = [e.start_ms for e in timeline.events]
    is_sorted = all(start_times[i] <= start_times[i + 1] for i in range(len(start_times) - 1))
    check("AC-P5-03: events sorted by start_ms",
          is_sorted,
          f"got {start_times}")

    # AC-P5-04: lanes grouped by span_type
    check("AC-P5-04a: lanes has llm_call group",
          "llm_call" in timeline.lanes,
          f"lanes keys: {list(timeline.lanes.keys())}")
    check("AC-P5-04b: lanes has tool_call group",
          "tool_call" in timeline.lanes,
          f"lanes keys: {list(timeline.lanes.keys())}")
    check("AC-P5-04c: llm_call lane has 2 events",
          len(timeline.lanes.get("llm_call", [])) == 2,
          f"got {len(timeline.lanes.get('llm_call', []))}")
    check("AC-P5-04d: tool_call lane has 2 events",
          len(timeline.lanes.get("tool_call", [])) == 2,
          f"got {len(timeline.lanes.get('tool_call', []))}")

    # Total duration
    check("Timeline total_duration_ms = 1500",
          timeline.total_duration_ms == 1500,
          f"got {timeline.total_duration_ms}")


async def test_derived_metrics():
    """Test DerivedMetricRegistry"""
    print("\n=== Derived Metrics Tests ===")
    from agenteval.services.derived_metrics import (
        DerivedMetricRegistry,
        register_builtin_providers,
    )

    register_builtin_providers()
    span_tree = make_mock_span_tree()

    # self_time_ms
    self_time = DerivedMetricRegistry.get("self_time_ms", span_tree)
    check("DerivedMetric self_time_ms = 250",
          self_time == 250,
          f"got {self_time}")

    # total_tokens
    tokens = DerivedMetricRegistry.get("total_tokens", span_tree)
    check("DerivedMetric total_tokens prompt = 300",
          tokens.get("prompt") == 300,
          f"got {tokens}")
    check("DerivedMetric total_tokens completion = 150",
          tokens.get("completion") == 150,
          f"got {tokens}")
    check("DerivedMetric total_tokens total = 450",
          tokens.get("total") == 450,
          f"got {tokens}")

    # tool_success_rate (1 ok, 1 error → 0.5)
    rate = DerivedMetricRegistry.get("tool_success_rate", span_tree)
    check("DerivedMetric tool_success_rate = 0.5",
          rate == 0.5,
          f"got {rate}")

    # compute_all
    all_metrics = DerivedMetricRegistry.compute_all(span_tree)
    check("compute_all returns 3 metrics",
          len(all_metrics) == 3,
          f"got {len(all_metrics)}: {list(all_metrics.keys())}")


async def test_report_generator_metrics():
    """Test ReportGenerator metrics computation (AC-P5-09, AC-P5-10, AC-P5-11)"""
    print("\n=== ReportGenerator Metrics Tests ===")
    from agenteval.services.report_generator import ReportGenerator
    from agenteval.schemas.report import ScenarioResultItem

    generator = ReportGenerator()

    # Create mock executions and results
    class MockExec:
        def __init__(self, status):
            self.status = status

    executions = [MockExec("completed"), MockExec("completed"), MockExec("completed"), MockExec("failed")]

    results = [
        ScenarioResultItem(
            scenario_id=uuid.uuid4(), external_id="s1", title="S1",
            status="completed", overall_score=0.9, overall_verdict="pass",
            latency_ms=100, cost_usd=0.01,
        ),
        ScenarioResultItem(
            scenario_id=uuid.uuid4(), external_id="s2", title="S2",
            status="completed", overall_score=0.85, overall_verdict="pass",
            latency_ms=200, cost_usd=0.02,
        ),
        ScenarioResultItem(
            scenario_id=uuid.uuid4(), external_id="s3", title="S3",
            status="completed", overall_score=0.6, overall_verdict="partial",
            latency_ms=300, cost_usd=0.03,
        ),
        ScenarioResultItem(
            scenario_id=uuid.uuid4(), external_id="s4", title="S4",
            status="failed", overall_score=None, overall_verdict=None,
            latency_ms=None, cost_usd=None,
        ),
    ]

    latencies = [100, 200, 300]
    costs = [0.01, 0.02, 0.03]
    metric_scores = {"correctness": [0.9, 0.85, 0.6]}

    metrics = generator._compute_metrics(executions, results, latencies, costs, metric_scores)

    # AC-P5-10: pass_rate (2 pass out of 3 scored)
    expected_pass_rate = 2 / 3
    check("AC-P5-10: pass_rate = 2/3 ≈ 0.667",
          abs(metrics.pass_rate - expected_pass_rate) < 0.01,
          f"got {metrics.pass_rate}")

    # AC-P5-09: metric_aggregates has mean/min/max/p50/p95
    corr_agg = metrics.metric_aggregates.get("correctness", {})
    check("AC-P5-09a: metric_aggregates has mean",
          "mean" in corr_agg,
          f"got {corr_agg}")
    check("AC-P5-09b: metric_aggregates has p50",
          "p50" in corr_agg,
          f"got {corr_agg}")
    check("AC-P5-09c: metric_aggregates has p95",
          "p95" in corr_agg,
          f"got {corr_agg}")

    # Check mean value: (0.9 + 0.85 + 0.6) / 3 = 0.7833
    check("AC-P5-09d: correctness mean ≈ 0.783",
          abs(corr_agg.get("mean", 0) - 0.7833) < 0.01,
          f"got {corr_agg.get('mean')}")

    # AC-P5-11: latency_p95
    # For [100, 200, 300], p95 ≈ 290
    check("AC-P5-11: latency_p95 calculated",
          metrics.latency_p95_ms > 0,
          f"got {metrics.latency_p95_ms}")

    # Scenario counts
    check("scenario_count = 4",
          metrics.scenario_count == 4,
          f"got {metrics.scenario_count}")
    check("executed_count = 3",
          metrics.executed_count == 3,
          f"got {metrics.executed_count}")
    check("scored_count = 3",
          metrics.scored_count == 3,
          f"got {metrics.scored_count}")


async def test_report_generator_html():
    """Test HTML report generation (AC-P5-06)"""
    print("\n=== HTML Report Generation Tests ===")
    from agenteval.services.report_generator import ReportGenerator
    from agenteval.schemas.report import (
        ReportData, EvaluationSummary, MetricsSnapshot,
        ScenarioResultItem, ReportSummary,
    )

    generator = ReportGenerator()

    data = ReportData(
        evaluation=EvaluationSummary(
            id=uuid.uuid4(), name="Test Eval", status="completed",
            dataset_name="Test Dataset", dataset_version="1.0",
        ),
        metrics=MetricsSnapshot(
            scenario_count=3, executed_count=3, scored_count=3,
            pass_rate=0.67,
            metric_aggregates={"correctness": {"mean": 0.78, "min": 0.6, "max": 0.9, "p50": 0.85, "p95": 0.9}},
        ),
        scenario_results=[
            ScenarioResultItem(
                scenario_id=uuid.uuid4(), external_id="s1", title="Scenario 1",
                status="completed", overall_score=0.9, overall_verdict="pass",
                latency_ms=100, cost_usd=0.01,
            ),
        ],
        summary=ReportSummary(
            total_scenarios=3, pass_rate=0.67, failed_scenarios=1,
            key_findings=["Pass rate 67% — 存在改进空间"],
        ),
    )

    html_bytes = generator.generate_html(data)
    html_str = html_bytes.decode("utf-8")

    # AC-P5-06: HTML contains summary, metrics table, scenario details
    check("AC-P5-06a: HTML contains 评测报告",
          "评测报告" in html_str,
          "missing title")
    check("AC-P5-06b: HTML contains 摘要 section",
          "摘要" in html_str,
          "missing summary section")
    check("AC-P5-06c: HTML contains 指标分布 table",
          "指标分布" in html_str,
          "missing metrics table")
    check("AC-P5-06d: HTML contains 场景明细 table",
          "场景明细" in html_str,
          "missing scenario details")
    check("AC-P5-06e: HTML contains pass_rate display",
          "67.0%" in html_str or "67%" in html_str,
          "missing pass rate")


async def test_report_generator_json():
    """Test JSON report generation (AC-P5-07, AC-P5-08)"""
    print("\n=== JSON Report Generation Tests ===")
    from agenteval.services.report_generator import ReportGenerator
    from agenteval.schemas.report import (
        ReportData, EvaluationSummary, MetricsSnapshot,
        ScenarioResultItem, ReportSummary,
    )

    generator = ReportGenerator()

    data = ReportData(
        evaluation=EvaluationSummary(
            id=uuid.uuid4(), name="Test Eval", status="completed",
        ),
        metrics=MetricsSnapshot(scenario_count=2),
        scenario_results=[],
        summary=ReportSummary(
            total_scenarios=2,
            key_findings=["Finding 1", "Finding 2"],
        ),
    )

    json_bytes = generator.generate_json(data)

    # AC-P5-07: JSON can be parsed
    try:
        parsed = json.loads(json_bytes)
        check("AC-P5-07: JSON report parseable", True)
    except json.JSONDecodeError as e:
        check("AC-P5-07: JSON report parseable", False, str(e))
        return

    # AC-P5-08: summary contains key_findings
    summary = parsed.get("summary", {})
    check("AC-P5-08a: summary has key_findings",
          "key_findings" in summary,
          f"keys: {list(summary.keys())}")
    check("AC-P5-08b: key_findings is array",
          isinstance(summary.get("key_findings"), list),
          f"got {type(summary.get('key_findings'))}")
    check("AC-P5-08c: key_findings has 2 items",
          len(summary.get("key_findings", [])) == 2,
          f"got {len(summary.get('key_findings', []))}")


async def test_trace_highlights():
    """Test trace highlights extraction (AC-P5-12)"""
    print("\n=== Trace Highlights Tests ===")
    from agenteval.services.report_generator import ReportGenerator

    generator = ReportGenerator()
    span_tree = make_mock_span_tree()

    highlights = generator._extract_trace_highlights(span_tree, "test-scenario")

    # AC-P5-12: highlights include slowest LLM call
    llm_highlights = [h for h in highlights if h.span_type == "llm_call"]
    check("AC-P5-12a: has LLM highlight",
          len(llm_highlights) > 0,
          f"got {len(llm_highlights)} LLM highlights")

    if llm_highlights:
        # Both LLM calls are 500ms, so either could be "slowest"
        check("AC-P5-12b: LLM highlight has duration",
              llm_highlights[0].duration_ms == 500,
              f"got {llm_highlights[0].duration_ms}")

    # Failed tool call highlight
    tool_highlights = [h for h in highlights if h.span_type == "tool_call"]
    check("AC-P5-12c: has failed tool highlight",
          len(tool_highlights) > 0,
          f"got {len(tool_highlights)} tool highlights")
    if tool_highlights:
        check("AC-P5-12d: tool highlight status is error",
              tool_highlights[0].status == "error",
              f"got {tool_highlights[0].status}")


async def test_report_api():
    """Test Report API endpoints (AC-P5-05, AC-P5-13)"""
    print("\n=== Report API Tests ===")
    import httpx

    base_url = "http://localhost:9000/api/v1"

    async with httpx.AsyncClient(timeout=10.0) as client:
        # First, get a valid project by listing workspaces -> projects
        # Or directly query evaluations from a known project
        # Let's list workspaces first
        resp_ws = await client.get(f"{base_url}/workspaces")
        if resp_ws.status_code != 200:
            check("AC-P5-05: POST report returns 202", False, "Cannot list workspaces")
            return

        ws_data = resp_ws.json().get("data", {})
        ws_items = ws_data.get("items", [])
        if not ws_items:
            check("AC-P5-05: POST report returns 202", False, "No workspaces found")
            return

        ws_id = ws_items[0]["id"]

        # List projects in workspace
        resp_proj = await client.get(f"{base_url}/workspaces/{ws_id}/projects")
        if resp_proj.status_code != 200:
            check("AC-P5-05: POST report returns 202", False, "Cannot list projects")
            return

        proj_items = resp_proj.json().get("data", {}).get("items", [])
        if not proj_items:
            check("AC-P5-05: POST report returns 202", False, "No projects found")
            return

        project_id = proj_items[0]["id"]

        # List evaluations for this project
        resp = await client.get(f"{base_url}/projects/{project_id}/evaluations")
        if resp.status_code != 200:
            check("AC-P5-05: POST report returns 202", False, "Cannot list evaluations")
            return

        data = resp.json()
        items = data.get("data", {}).get("items", [])
        if not items:
            check("AC-P5-05: POST report returns 202", False, "No evaluations found")
            return

        eval_id = items[0]["id"]

        # AC-P5-05: POST generate HTML report returns 202
        resp = await client.post(
            f"{base_url}/evaluations/{eval_id}/reports",
            json={"format": "html"},
        )
        check("AC-P5-05: POST report returns 202",
              resp.status_code == 202,
              f"got {resp.status_code}")

        if resp.status_code == 202:
            report_data = resp.json().get("data", {})
            report_id = report_data.get("id")
            check("Report has id", report_id is not None, "missing id")
            check("Report status is generating",
                  report_data.get("status") == "generating",
                  f"got {report_data.get('status')}")

            # Wait for report generation (poll until completed)
            report_info = None
            for _ in range(10):  # Max 5 seconds
                await asyncio.sleep(0.5)
                resp2 = await client.get(f"{base_url}/reports/{report_id}")
                if resp2.status_code == 200:
                    report_info = resp2.json().get("data", {})
                    if report_info.get("status") == "completed":
                        break

            if report_info and report_info.get("status") == "completed":
                check("Report completed", True)

                # AC-P5-13: Download returns correct Content-Type
                resp3 = await client.get(f"{base_url}/reports/{report_id}/download")
                if resp3.status_code == 200:
                    content_type = resp3.headers.get("content-type", "")
                    check("AC-P5-13: download Content-Type is text/html",
                          "text/html" in content_type,
                          f"got {content_type}")
                else:
                    check("AC-P5-13: download Content-Type is text/html",
                          False, f"download failed: {resp3.status_code}")

                # Preview endpoint
                resp4 = await client.get(f"{base_url}/reports/{report_id}/preview")
                check("Preview returns 200",
                      resp4.status_code == 200,
                      f"got {resp4.status_code}")
            else:
                status = report_info.get("status") if report_info else "unknown"
                check("Report completed", False, f"status: {status}")

        # Test JSON report
        resp_json = await client.post(
            f"{base_url}/evaluations/{eval_id}/reports",
            json={"format": "json"},
        )
        check("JSON report returns 202",
              resp_json.status_code == 202,
              f"got {resp_json.status_code}")


async def test_report_model():
    """Test ReportModel"""
    print("\n=== Report Model Tests ===")
    from agenteval.infra.models.report_model import ReportModel

    report = ReportModel(
        evaluation_id=uuid.uuid4(),
        format="html",
        status="generating",
    )
    check("ReportModel: can create instance",
          report.format == "html" and report.status == "generating")


async def main():
    print("=" * 60)
    print("Phase 5 Acceptance Test — Trace & Report System")
    print("=" * 60)

    await test_trace_enricher()
    await test_timeline_builder()
    await test_derived_metrics()
    await test_report_generator_metrics()
    await test_report_generator_html()
    await test_report_generator_json()
    await test_trace_highlights()
    await test_report_model()
    await test_report_api()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

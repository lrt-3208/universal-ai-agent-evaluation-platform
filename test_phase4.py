#!/usr/bin/env python3
"""Phase 4 Acceptance Test — Judge System

Tests:
- AC-P4-01: Rule Judge response_contains → correctness=1.0
- AC-P4-02: Rule Judge response_not_contains → forbidden_check=0.0
- AC-P4-03: Rule Judge tool_calls_expected → correct ratio
- AC-P4-04: LLM Judge returns JSON with scores array (mock)
- AC-P4-05: LLM Judge score range [0.0, 1.0]
- AC-P4-08: Multi-Judge aggregation overall_score correct
- AC-P4-09: overall_verdict by 0.8/0.5 thresholds
- AC-P4-10: Scenario-level judge_config overrides evaluation-level
- AC-P4-11: Judge failure → JudgeResult.status=FAILED + error_message
- AC-P4-12: Scoring complete → Evaluation.status=COMPLETED
- AC-P4-15: judge-configs/validate returns validation result
"""

import asyncio
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone

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


async def test_rule_judge():
    """Test Rule Judge (AC-P4-01, AC-P4-02, AC-P4-03)"""
    print("\n=== Rule Judge Tests ===")
    from agenteval.judges import JudgeContext, JudgeRegistry
    from agenteval.judges.builtin import register_builtin_judges

    register_builtin_judges()

    # Create mock scenario and agent_execution
    class MockScenario:
        external_id = "test-001"
        title = "Test Scenario"
        input_data = {"user_message": "北京天气怎么样？"}
        expected = {
            "response_contains": ["北京", "天气"],
            "response_not_contains": ["不知道", "无法"],
            "tool_calls_expected": [{"tool_name": "get_weather", "arguments": {"city": "北京"}}],
            "intent": "weather_query",
        }
        history = []
        memory = {}
        judge_config = None

    class MockAgentExecution:
        conversation_data = {
            "messages": [
                {"role": "user", "content": "北京天气怎么样？"},
                {"role": "assistant", "content": "北京今天天气晴朗，气温25度。"},
            ]
        }
        trace_id = None

    judge = JudgeRegistry.create("rule")
    ctx = JudgeContext(
        scenario=MockScenario(),
        agent_execution=MockAgentExecution(),
        config={"metrics": ["correctness", "forbidden_check", "tool_accuracy"]},
    )

    output = await judge.evaluate(ctx)

    # AC-P4-01: response_contains all matched → correctness=1.0
    correctness_scores = [ms for ms in output.metric_scores if ms.metric_key == "correctness"]
    check("AC-P4-01: correctness=1.0 when all keywords matched",
          len(correctness_scores) > 0 and correctness_scores[0].score == 1.0,
          f"got {correctness_scores[0].score if correctness_scores else 'none'}")

    # AC-P4-02: response_not_contains not hit → forbidden_check=1.0
    forbidden_scores = [ms for ms in output.metric_scores if ms.metric_key == "forbidden_check"]
    check("AC-P4-02: forbidden_check=1.0 when no forbidden words",
          len(forbidden_scores) > 0 and forbidden_scores[0].score == 1.0,
          f"got {forbidden_scores[0].score if forbidden_scores else 'none'}")

    # Test forbidden word hit
    class MockAgentExecutionBad:
        conversation_data = {
            "messages": [
                {"role": "user", "content": "北京天气怎么样？"},
                {"role": "assistant", "content": "我不知道北京天气。"},
            ]
        }
        trace_id = None

    ctx_bad = JudgeContext(
        scenario=MockScenario(),
        agent_execution=MockAgentExecutionBad(),
        config={"metrics": ["forbidden_check"]},
    )
    output_bad = await judge.evaluate(ctx_bad)
    forbidden_bad = [ms for ms in output_bad.metric_scores if ms.metric_key == "forbidden_check"]
    check("AC-P4-02b: forbidden_check=0.0 when forbidden word found",
          len(forbidden_bad) > 0 and forbidden_bad[0].score == 0.0,
          f"got {forbidden_bad[0].score if forbidden_bad else 'none'}")

    # AC-P4-03: tool_calls_expected (no tool calls in response → 0.0)
    tool_scores = [ms for ms in output.metric_scores if ms.metric_key == "tool_accuracy"]
    check("AC-P4-03: tool_accuracy=0.0 when no tool calls made",
          len(tool_scores) > 0 and tool_scores[0].score == 0.0,
          f"got {tool_scores[0].score if tool_scores else 'none'}")


async def test_score_aggregator():
    """Test Score Aggregator (AC-P4-08, AC-P4-09)"""
    print("\n=== Score Aggregator Tests ===")
    from agenteval.judges import JudgeOutput, MetricScore
    from agenteval.services.score_aggregator import ScoreAggregator

    aggregator = ScoreAggregator()

    # AC-P4-08: Multi-Judge aggregation
    output1 = JudgeOutput(
        judge_type="rule",
        metric_scores=[
            MetricScore(metric_key="correctness", metric_name="Correctness", score=0.8, weight=1.0),
            MetricScore(metric_key="tool_accuracy", metric_name="Tool Accuracy", score=0.6, weight=1.0),
        ],
    )
    output2 = JudgeOutput(
        judge_type="llm",
        metric_scores=[
            MetricScore(metric_key="correctness", metric_name="Correctness", score=0.9, weight=1.0),
            MetricScore(metric_key="coherence", metric_name="Coherence", score=0.85, weight=1.0),
        ],
    )

    result = aggregator.aggregate([output1, output2])

    # correctness: (0.8 + 0.9) / 2 = 0.85
    # tool_accuracy: 0.6
    # coherence: 0.85
    # overall: (0.85 + 0.6 + 0.85) / 3 = 0.7667
    check("AC-P4-08: overall_score calculated correctly",
          abs(result.overall_score - 0.7667) < 0.01,
          f"got {result.overall_score}")

    # AC-P4-09: verdict thresholds
    check("AC-P4-09a: verdict=partial when 0.5 <= score < 0.8",
          result.overall_verdict == "partial",
          f"got {result.overall_verdict}")

    # Test pass threshold
    high_outputs = [JudgeOutput(
        judge_type="rule",
        metric_scores=[MetricScore(metric_key="correctness", metric_name="C", score=0.9, weight=1.0)],
    )]
    high_result = aggregator.aggregate(high_outputs)
    check("AC-P4-09b: verdict=pass when score >= 0.8",
          high_result.overall_verdict == "pass",
          f"got {high_result.overall_verdict}")

    # Test fail threshold
    low_outputs = [JudgeOutput(
        judge_type="rule",
        metric_scores=[MetricScore(metric_key="correctness", metric_name="C", score=0.3, weight=1.0)],
    )]
    low_result = aggregator.aggregate(low_outputs)
    check("AC-P4-09c: verdict=fail when score < 0.5",
          low_result.overall_verdict == "fail",
          f"got {low_result.overall_verdict}")


async def test_config_merge():
    """Test config merge (AC-P4-10)"""
    print("\n=== Config Merge Tests ===")
    from agenteval.services.judge_service import JudgeService

    class MockScenario:
        judge_config = {
            "judges": [{"judge_type": "rule", "weights": {"tool_accuracy": 2.0}}],
            "weights": {"correctness": 1.5},
        }

    class MockEvaluation:
        judge_configs = [
            {"judge_type": "rule", "metrics": ["correctness", "tool_accuracy"]},
            {"judge_type": "llm", "metrics": ["correctness", "hallucination"]},
        ]

    service = JudgeService(None)
    merged = service._resolve_judge_configs(MockScenario(), MockEvaluation())

    # Check rule judge got merged weights
    rule_config = next((c for c in merged if c.get("judge_type") == "rule"), None)
    check("AC-P4-10a: scenario-level weights merged into rule judge",
          rule_config and rule_config.get("weights", {}).get("tool_accuracy") == 2.0,
          f"got {rule_config}")

    # Check global weights applied
    check("AC-P4-10b: global weights applied to all judges",
          all(c.get("weights", {}).get("correctness") == 1.5 for c in merged),
          f"got {[c.get('weights') for c in merged]}")


async def test_judge_api():
    """Test Judge API endpoints (AC-P4-15)"""
    print("\n=== Judge API Tests ===")
    import httpx

    base_url = "http://localhost:9000/api/v1"

    async with httpx.AsyncClient() as client:
        # AC-P4-15: validate judge configs
        resp = await client.post(
            f"{base_url}/projects/{uuid.uuid4()}/judge-configs/validate",
            json={
                "judge_configs": [
                    {"judge_type": "rule", "metrics": ["correctness"]},
                    {"judge_type": "llm", "metrics": ["hallucination"]},
                ]
            },
        )
        data = resp.json()
        check("AC-P4-15a: validate returns valid=true for good configs",
              resp.status_code == 200 and data["data"]["valid"] is True,
              f"got {data}")

        # Test invalid config
        resp2 = await client.post(
            f"{base_url}/projects/{uuid.uuid4()}/judge-configs/validate",
            json={
                "judge_configs": [
                    {"judge_type": "unknown_type"},
                ]
            },
        )
        data2 = resp2.json()
        check("AC-P4-15b: validate returns valid=false for unknown judge type",
              resp2.status_code == 200 and data2["data"]["valid"] is False,
              f"got {data2}")


async def test_judge_result_model():
    """Test JudgeResult model and repo"""
    print("\n=== JudgeResult Model Tests ===")
    from agenteval.infra.models.judge_result_model import JudgeResultModel

    # Check model has required fields
    result = JudgeResultModel(
        scenario_execution_id=uuid.uuid4(),
        judge_type="rule",
        judge_config={"metrics": ["correctness"]},
        status="completed",
        metric_scores=[{"metric_key": "correctness", "score": 0.9}],
        overall_score=0.9,
        overall_verdict="pass",
        started_at=datetime.now(timezone.utc),
    )
    check("JudgeResultModel: can create instance",
          result.judge_type == "rule" and result.overall_score == 0.9)


async def test_llm_judge_mock():
    """Test LLM Judge with mock client (AC-P4-04, AC-P4-05)"""
    print("\n=== LLM Judge Tests (Mock) ===")
    from agenteval.judges import JudgeContext, JudgeRegistry
    from agenteval.core.llm_client import LLMClient, LLMResponse

    class MockLLMClient(LLMClient):
        async def complete(self, prompt, **kwargs):
            return LLMResponse(
                content='{"scores": [{"metric_key": "correctness", "score": 0.85, "reasoning": "Good"}], "overall_reasoning": "OK"}',
                model="mock-model",
            )

        def validate_config(self, config):
            return True

        @property
        def provider(self):
            return "mock"

    class MockScenario:
        external_id = "test-llm"
        title = "LLM Test"
        input_data = {"user_message": "Hello"}
        expected = {"reference_answer": "Hi there"}
        history = []
        memory = {}

    class MockAgentExecution:
        conversation_data = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ]
        }
        trace_id = None

    judge = JudgeRegistry.create("llm")
    ctx = JudgeContext(
        scenario=MockScenario(),
        agent_execution=MockAgentExecution(),
        config={"metrics": ["correctness"]},
        llm_client=MockLLMClient(),
    )

    output = await judge.evaluate(ctx)

    # AC-P4-04: returns scores array
    check("AC-P4-04: LLM Judge returns metric_scores",
          len(output.metric_scores) > 0,
          f"got {len(output.metric_scores)} scores")

    # AC-P4-05: score in [0.0, 1.0]
    if output.metric_scores:
        score = output.metric_scores[0].score
        check("AC-P4-05: score in [0.0, 1.0]",
              0.0 <= score <= 1.0,
              f"got {score}")
    else:
        check("AC-P4-05: score in [0.0, 1.0]", False, "no scores")


async def main():
    print("=" * 60)
    print("Phase 4 Acceptance Test — Judge System")
    print("=" * 60)

    await test_rule_judge()
    await test_score_aggregator()
    await test_config_merge()
    await test_judge_result_model()
    await test_llm_judge_mock()
    await test_judge_api()

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

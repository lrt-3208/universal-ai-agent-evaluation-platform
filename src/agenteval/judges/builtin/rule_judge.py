"""Rule Judge — deterministic rule-based scoring.

Reference: ../docs/phases/phase-4-judge.md §5
Evaluates: correctness, forbidden_check, tool_accuracy, intent_match
No external service calls — pure rule matching.
"""

from agenteval.judges import Judge, JudgeContext, JudgeOutput, MetricScore


class RuleJudge(Judge):
    """Deterministic rule-based judge.

    Reads Scenario.expected and matches against AgentExecution conversation.
    """

    @property
    def judge_type(self) -> str:
        return "rule"

    @property
    def supported_metrics(self) -> set[str]:
        return {"correctness", "forbidden_check", "tool_accuracy", "intent_match"}

    async def evaluate(self, ctx: JudgeContext) -> JudgeOutput:
        """Evaluate all applicable rule-based metrics."""
        params = ctx.config.get("params", {})
        case_sensitive = params.get("case_sensitive", False)

        response_text = self._get_response_text(ctx)
        expected = ctx.scenario.expected or {}
        weights = ctx.config.get("weights", {})
        scores: list[MetricScore] = []

        # correctness: response_contains
        if "response_contains" in expected:
            contains = expected["response_contains"]
            hits = sum(1 for kw in contains if self._match(kw, response_text, case_sensitive))
            score = hits / len(contains) if contains else 1.0
            scores.append(MetricScore(
                metric_key="correctness",
                metric_name="Correctness",
                score=round(score, 4),
                weight=weights.get("correctness", 1.0),
                detail={"expected_keywords": contains, "matched": hits},
                reasoning=f"Matched {hits}/{len(contains)} expected keywords",
            ))

        # forbidden_check: response_not_contains
        if "response_not_contains" in expected:
            forbidden = expected["response_not_contains"]
            violations = [kw for kw in forbidden if self._match(kw, response_text, case_sensitive)]
            score = 0.0 if violations else 1.0
            scores.append(MetricScore(
                metric_key="forbidden_check",
                metric_name="Forbidden Check",
                score=score,
                weight=weights.get("forbidden_check", 0.5),
                detail={"forbidden": forbidden, "violations": violations},
                reasoning=f"{len(violations)} forbidden patterns found",
            ))

        # tool_accuracy: tool_calls_expected
        if "tool_calls_expected" in expected:
            expected_calls = expected["tool_calls_expected"]
            actual_calls = self._extract_tool_calls(ctx)
            matches = sum(
                1 for ec in expected_calls
                if self._tool_call_matches(ec, actual_calls)
            )
            score = matches / len(expected_calls) if expected_calls else 1.0
            scores.append(MetricScore(
                metric_key="tool_accuracy",
                metric_name="Tool Accuracy",
                score=round(score, 4),
                weight=weights.get("tool_accuracy", 1.5),
                detail={"expected_count": len(expected_calls), "matched": matches},
                reasoning=f"Matched {matches}/{len(expected_calls)} expected tool calls",
            ))

        # intent_match
        if "intent" in expected:
            expected_intent = expected["intent"]
            detected = self._detect_intent(expected_intent, response_text)
            score = 1.0 if detected else 0.0
            scores.append(MetricScore(
                metric_key="intent_match",
                metric_name="Intent Match",
                score=score,
                weight=weights.get("intent_match", 1.0),
                detail={"expected_intent": expected_intent},
                reasoning=f"Intent '{expected_intent}' {'detected' if detected else 'not detected'}",
            ))

        return JudgeOutput(
            judge_type=self.judge_type,
            metric_scores=scores,
            reasoning="Rule-based evaluation completed",
        )

    def _get_response_text(self, ctx: JudgeContext) -> str:
        """Extract last assistant message from conversation."""
        conv_data = ctx.agent_execution.conversation_data or {}
        messages = conv_data.get("messages", [])
        # Find last assistant message
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                return msg.get("content", "")
        # Fallback: last message
        return messages[-1].get("content", "") if messages else ""

    def _match(self, keyword: str, text: str, case_sensitive: bool) -> bool:
        """Check if keyword exists in text."""
        if case_sensitive:
            return keyword in text
        return keyword.lower() in text.lower()

    def _extract_tool_calls(self, ctx: JudgeContext) -> list[dict]:
        """Extract all tool calls from conversation messages."""
        conv_data = ctx.agent_execution.conversation_data or {}
        messages = conv_data.get("messages", [])
        calls = []
        for msg in messages:
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    calls.append(tc)
        return calls

    def _tool_call_matches(self, expected_call: dict, actual_calls: list[dict]) -> bool:
        """Check if an expected tool call matches any actual call."""
        for ac in actual_calls:
            if ac.get("tool_name") == expected_call.get("tool_name"):
                args_match = expected_call.get("args_match")
                if not args_match:
                    return True
                # Check all expected args match
                actual_args = ac.get("arguments", {})
                if all(actual_args.get(k) == v for k, v in args_match.items()):
                    return True
        return False

    def _detect_intent(self, intent: str, response_text: str) -> bool:
        """Simple keyword-based intent detection."""
        intent_keywords = {
            "weather_query": ["天气", "weather", "气温", "温度"],
            "search": ["搜索", "查找", "search", "find", "结果"],
            "booking": ["预订", "预约", "book", "reserve", "确认"],
            "calculation": ["计算", "等于", "calculate", "result", "答案是"],
            "greeting": ["你好", "hello", "hi", "欢迎"],
            "farewell": ["再见", "bye", "goodbye"],
        }
        keywords = intent_keywords.get(intent, [intent])
        return any(kw.lower() in response_text.lower() for kw in keywords)

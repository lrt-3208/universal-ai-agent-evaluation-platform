"""LLM Judge — semantic scoring via LLMClient.

Reference: ../docs/phases/phase-4-judge.md §6
Evaluates: correctness, hallucination, planning_score, memory_accuracy, coherence
Uses LLMClient (not direct openai SDK) per contract MUST constraint.
"""

import json

import structlog

from agenteval.judges import Judge, JudgeContext, JudgeOutput, MetricScore

logger = structlog.get_logger()

# Default prompt template for LLM Judge
DEFAULT_LLM_JUDGE_PROMPT = """You are an expert evaluator for AI agent responses.

## Scenario
- Title: {title}
- User Input: {user_message}
- Expected Intent: {intent}
- Reference Answer: {reference_answer}

## Agent Response
{agent_response}

## Tool Calls
{tool_calls_summary}

## Conversation History
{history_summary}

## Evaluation Task
Evaluate the agent's response on the following metrics. For each metric, provide:
1. A score from 0.0 to 1.0 (1.0 = perfect, 0.0 = completely wrong)
2. A brief reasoning (1-2 sentences)

### Metrics to evaluate:
{metrics_instructions}

## Output Format
You MUST respond in valid JSON only:
```json
{{
  "scores": [
    {{
      "metric_key": "<metric_name>",
      "score": <float>,
      "reasoning": "<explanation>"
    }}
  ],
  "overall_reasoning": "<summary>"
}}
```
"""

METRIC_INSTRUCTIONS = {
    "correctness": "correctness: Is the response factually correct and addresses the user's question? Compare with reference answer if available.",
    "hallucination": "hallucination: Score 1.0 means NO hallucination (all content is grounded), 0.0 means severe hallucination.",
    "planning_score": "planning_score: If the agent used multi-step reasoning or tool calls, evaluate the quality of the plan. If no planning needed, score 1.0.",
    "memory_accuracy": "memory_accuracy: Did the agent correctly use provided memory/context? If no memory provided, score 1.0.",
    "coherence": "coherence: Is the response coherent, well-structured, and easy to understand?",
}


class LLMJudge(Judge):
    """LLM-based semantic judge.

    MUST: Uses JudgeContext.llm_client (not direct openai SDK).
    """

    @property
    def judge_type(self) -> str:
        return "llm"

    @property
    def supported_metrics(self) -> set[str]:
        return {"correctness", "hallucination", "planning_score", "memory_accuracy", "coherence"}

    def validate_config(self, config: dict) -> bool:
        """LLM Judge requires llm_client in context."""
        return True

    async def evaluate(self, ctx: JudgeContext) -> JudgeOutput:
        """Evaluate using LLM via LLMClient."""
        if not ctx.llm_client:
            return JudgeOutput(
                judge_type=self.judge_type,
                metric_scores=[],
                error="No LLM client provided in JudgeContext",
            )

        params = ctx.config.get("params", {})
        model = params.get("model")
        temperature = params.get("temperature", 0.0)
        max_tokens = params.get("max_tokens", 1024)

        # Determine which metrics to evaluate
        configured_metrics = ctx.config.get("metrics", [])
        metrics = configured_metrics if configured_metrics else list(self.supported_metrics)
        # Filter to only supported metrics
        metrics = [m for m in metrics if m in self.supported_metrics]

        if not metrics:
            return JudgeOutput(
                judge_type=self.judge_type,
                metric_scores=[],
                reasoning="No applicable metrics configured",
            )

        prompt = self._build_prompt(ctx, metrics)

        try:
            response = await ctx.llm_client.complete(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.content)
            weights = ctx.config.get("weights", {})

            scores = []
            for s in result.get("scores", []):
                metric_key = s.get("metric_key", "")
                if metric_key in metrics:
                    score_val = max(0.0, min(1.0, float(s.get("score", 0.0))))
                    scores.append(MetricScore(
                        metric_key=metric_key,
                        metric_name=metric_key.replace("_", " ").title(),
                        score=round(score_val, 4),
                        weight=weights.get(metric_key, 1.0),
                        reasoning=s.get("reasoning"),
                    ))

            return JudgeOutput(
                judge_type=self.judge_type,
                metric_scores=scores,
                reasoning=result.get("overall_reasoning"),
                metadata={"model": response.model, "tokens": response.tokens},
            )

        except json.JSONDecodeError as e:
            logger.error("llm_judge.json_parse_error", error=str(e))
            return JudgeOutput(
                judge_type=self.judge_type,
                metric_scores=[],
                error=f"LLM response not valid JSON: {e}",
            )
        except Exception as e:
            logger.error("llm_judge.error", error=str(e))
            return JudgeOutput(
                judge_type=self.judge_type,
                metric_scores=[],
                error=f"LLM Judge error: {e}",
            )

    def _build_prompt(self, ctx: JudgeContext, metrics: list[str]) -> str:
        """Build evaluation prompt from context."""
        conv_data = ctx.agent_execution.conversation_data or {}
        messages = conv_data.get("messages", [])

        # Get response text
        response_text = ""
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                response_text = msg.get("content", "")
                break

        # Tool calls summary
        tool_calls = []
        for msg in messages:
            for tc in msg.get("tool_calls", []):
                tool_calls.append({"tool": tc.get("tool_name"), "args": tc.get("arguments")})
        tool_calls_summary = json.dumps(tool_calls, ensure_ascii=False, indent=2) if tool_calls else "No tool calls"

        # History summary
        history = ctx.scenario.history or []
        history_summary = "\n".join(
            f"[{m.get('role', 'unknown')}] {str(m.get('content', ''))[:200]}"
            for m in history
        ) or "No history"

        # Metric instructions
        metrics_instructions = "\n".join(
            METRIC_INSTRUCTIONS.get(m, f"{m}: Evaluate this metric.") for m in metrics
        )

        expected = ctx.scenario.expected or {}

        return DEFAULT_LLM_JUDGE_PROMPT.format(
            title=ctx.scenario.title or "Untitled",
            user_message=(ctx.scenario.input_data or {}).get("user_message", ""),
            intent=expected.get("intent", "N/A"),
            reference_answer=expected.get("reference_answer", "N/A"),
            agent_response=response_text,
            tool_calls_summary=tool_calls_summary,
            history_summary=history_summary,
            metrics_instructions=metrics_instructions,
        )

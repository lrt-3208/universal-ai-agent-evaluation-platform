"""DSL Validator - Validate DSL content

Reference: ../docs/contracts/scenario-dsl.md §4
"""

import re

import structlog

from agenteval.schemas.scenario import ValidationErrorDetail, ValidationResultVO
from agenteval.services.dsl_parser import ScenarioEntity, get_parser

logger = structlog.get_logger()

MAX_SCENARIOS_PER_IMPORT = 5000


class DSLValidator:
    """Validate DSL content for syntax, completeness, and semantics"""

    def validate(self, content: str, format: str) -> ValidationResultVO:
        """Validate DSL content and return result"""
        result = ValidationResultVO(valid=True, errors=[], warnings=[], scenario_count=0)

        # Step 1: Parse
        try:
            parser = get_parser(format)
            output = parser.parse(content)
        except Exception as e:
            result.valid = False
            result.errors.append(
                ValidationErrorDetail(field="_root", message=f"Parse error: {e}")
            )
            return result

        scenarios = output.scenarios

        if not scenarios:
            result.warnings.append("No scenarios found in DSL")
            return result

        # Step 2: Size check
        if len(scenarios) > MAX_SCENARIOS_PER_IMPORT:
            result.valid = False
            result.errors.append(
                ValidationErrorDetail(
                    field="_root",
                    message=f"Dataset import exceeds {MAX_SCENARIOS_PER_IMPORT} scenario limit",
                )
            )
            return result

        # Step 3: external_id uniqueness
        ids = [s.external_id for s in scenarios]
        seen = set()
        duplicates = set()
        for eid in ids:
            if eid in seen:
                duplicates.add(eid)
            seen.add(eid)
        for dup in duplicates:
            result.errors.append(
                ValidationErrorDetail(
                    scenario_external_id=dup,
                    field="id",
                    message=f"Duplicate scenario id: {dup}",
                )
            )

        # Step 4: Per-scenario validation
        for s in scenarios:
            self._validate_scenario(s, result)

        result.scenario_count = len(scenarios)
        result.valid = len(result.errors) == 0
        return result

    def _validate_scenario(self, s: ScenarioEntity, result: ValidationResultVO):
        """Validate a single scenario"""
        # Required: external_id
        if not s.external_id:
            result.errors.append(
                ValidationErrorDetail(
                    scenario_external_id=s.external_id or "unknown",
                    field="id",
                    message="Scenario id is required",
                )
            )

        # Required: title
        if not s.title:
            result.errors.append(
                ValidationErrorDetail(
                    scenario_external_id=s.external_id,
                    field="title",
                    message="Title is required",
                )
            )

        # Required: input.user_message
        user_msg = s.input_data.get("user_message", "")
        if not user_msg:
            result.errors.append(
                ValidationErrorDetail(
                    scenario_external_id=s.external_id,
                    field="input.user_message",
                    message="user_message is required",
                )
            )

        # Type checks
        if s.priority < 0:
            result.errors.append(
                ValidationErrorDetail(
                    scenario_external_id=s.external_id,
                    field="priority",
                    message="Priority must be >= 0",
                )
            )

        # constraints.max_turns >= 1
        max_turns = s.constraints.get("max_turns")
        if max_turns is not None and max_turns < 1:
            result.errors.append(
                ValidationErrorDetail(
                    scenario_external_id=s.external_id,
                    field="constraints.max_turns",
                    message="max_turns must be >= 1",
                )
            )

        # constraints.max_latency_ms >= 100
        max_latency = s.constraints.get("max_latency_ms")
        if max_latency is not None and max_latency < 100:
            result.errors.append(
                ValidationErrorDetail(
                    scenario_external_id=s.external_id,
                    field="constraints.max_latency_ms",
                    message="max_latency_ms must be >= 100",
                )
            )

        # constraints.max_cost_usd > 0
        max_cost = s.constraints.get("max_cost_usd")
        if max_cost is not None and max_cost <= 0:
            result.errors.append(
                ValidationErrorDetail(
                    scenario_external_id=s.external_id,
                    field="constraints.max_cost_usd",
                    message="max_cost_usd must be > 0",
                )
            )

        # memory.max_tokens >= 1
        max_tokens = s.memory.get("max_tokens")
        if max_tokens is not None and max_tokens < 1:
            result.errors.append(
                ValidationErrorDetail(
                    scenario_external_id=s.external_id,
                    field="memory.max_tokens",
                    message="max_tokens must be >= 1",
                )
            )

        # Semantic: tool_calls_expected tool_name not in must_not_use_tools
        expected_tools = {
            tc.get("tool_name")
            for tc in s.expected.get("tool_calls_expected", [])
        }
        forbidden_tools = set(s.constraints.get("must_not_use_tools", []))
        conflict = expected_tools & forbidden_tools
        if conflict:
            result.errors.append(
                ValidationErrorDetail(
                    scenario_external_id=s.external_id,
                    field="expected.tool_calls_expected",
                    message=f"Contradiction: expected tools {conflict} are in must_not_use_tools",
                )
            )

        # Semantic: max_turns >= history user messages + 1
        if max_turns is not None:
            user_msgs_in_history = sum(
                1 for h in s.history if h.get("role") == "user"
            )
            if max_turns < user_msgs_in_history + 1:
                result.errors.append(
                    ValidationErrorDetail(
                        scenario_external_id=s.external_id,
                        field="constraints.max_turns",
                        message=f"max_turns ({max_turns}) < history user messages ({user_msgs_in_history}) + 1",
                    )
                )

        # Semantic: forbidden_patterns must be valid regex
        for pattern in s.constraints.get("forbidden_patterns", []):
            try:
                re.compile(pattern)
            except re.error:
                result.errors.append(
                    ValidationErrorDetail(
                        scenario_external_id=s.external_id,
                        field="constraints.forbidden_patterns",
                        message=f"Invalid regex pattern: {pattern}",
                    )
                )

        # Semantic: response_contains and response_not_contains no intersection
        contains = set(s.expected.get("response_contains", []))
        not_contains = set(s.expected.get("response_not_contains", []))
        overlap = contains & not_contains
        if overlap:
            result.warnings.append(
                f"Scenario {s.external_id}: response_contains and response_not_contains "
                f"have overlap: {overlap}"
            )

        # Warning: no expected output
        if not s.expected:
            result.warnings.append(
                f"Scenario {s.external_id} has no expected output, "
                "judge capabilities will be limited"
            )

        # Warning: reference_answer needed for embedding judge
        if s.judge_config:
            judges = s.judge_config.get("judges", [])
            has_embedding = any(j.get("judge_type") == "embedding" for j in judges)
            if has_embedding and not s.expected.get("reference_answer"):
                result.warnings.append(
                    f"Scenario {s.external_id}: embedding judge needs reference_answer"
                )

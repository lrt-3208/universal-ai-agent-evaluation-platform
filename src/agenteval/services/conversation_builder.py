"""Conversation Builder - Build initial conversation context from Scenario

Reference: ../docs/phases/phase-2-scenario.md §3.1 (Conversation Builder)
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

from agenteval.core.exceptions import NotFoundException
from agenteval.infra.models.scenario_model import ScenarioModel
from agenteval.infra.repositories.scenario_repo import ScenarioRepository

logger = structlog.get_logger()


@dataclass
class ConversationMessage:
    """A single message in the conversation"""

    role: str  # user, assistant, system, tool
    content: str
    timestamp: str = ""
    tool_calls: list | None = None
    tool_call_id: str | None = None
    name: str | None = None


@dataclass
class ConversationContext:
    """Initial conversation context built from a Scenario"""

    scenario_id: uuid.UUID
    external_id: str
    messages: list[ConversationMessage] = field(default_factory=list)
    memory: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    expected: dict = field(default_factory=dict)
    judge_config: dict | None = None
    tags: list = field(default_factory=list)
    priority: int = 0

    def to_dict(self) -> dict:
        """Serialize to dict for Phase 3 runner"""
        return {
            "scenario_id": str(self.scenario_id),
            "external_id": self.external_id,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp,
                    **({"tool_calls": m.tool_calls} if m.tool_calls else {}),
                    **({"tool_call_id": m.tool_call_id} if m.tool_call_id else {}),
                    **({"name": m.name} if m.name else {}),
                }
                for m in self.messages
            ],
            "memory": self.memory,
            "constraints": self.constraints,
            "expected": self.expected,
            "judge_config": self.judge_config,
            "tags": self.tags,
            "priority": self.priority,
        }


class ConversationBuilder:
    """Build initial conversation context from Scenario entities"""

    def __init__(self, session=None):
        self.session = session
        self.scenario_repo = ScenarioRepository(session) if session else None

    async def build_from_scenario_id(
        self, scenario_id: uuid.UUID
    ) -> ConversationContext:
        """Build conversation context from a scenario ID"""
        if not self.scenario_repo:
            raise RuntimeError("Session not provided")

        scenario = await self.scenario_repo.get_by_id(scenario_id)
        if not scenario:
            raise NotFoundException(
                message=f"Scenario not found: {scenario_id}",
                code=40404,
            )
        return self.build_from_model(scenario)

    def build_from_model(self, scenario: ScenarioModel) -> ConversationContext:
        """Build conversation context from a ScenarioModel"""
        messages = []

        # Build history messages
        for h in scenario.history:
            msg = ConversationMessage(
                role=h.get("role", "user"),
                content=h.get("content", ""),
                timestamp=h.get(
                    "timestamp",
                    datetime.now(timezone.utc).isoformat(),
                ),
                tool_calls=h.get("tool_calls"),
                tool_call_id=h.get("tool_call_id"),
                name=h.get("name"),
            )
            messages.append(msg)

        # Add the current user input as the last message
        user_message = scenario.input_data.get("user_message", "")
        if user_message:
            messages.append(
                ConversationMessage(
                    role="user",
                    content=user_message,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )

        return ConversationContext(
            scenario_id=scenario.id,
            external_id=scenario.external_id,
            messages=messages,
            memory=scenario.memory or {},
            constraints=scenario.constraints or {},
            expected=scenario.expected or {},
            judge_config=scenario.judge_config,
            tags=scenario.tags or [],
            priority=scenario.priority,
        )

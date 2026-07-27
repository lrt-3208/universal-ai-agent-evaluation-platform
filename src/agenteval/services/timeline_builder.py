"""Timeline Builder — build execution timeline from trace.

Reference: ../docs/phases/phase-5-report.md §4.4
"""

from __future__ import annotations

import uuid
from datetime import datetime

from agenteval.schemas.trace import TimelineEvent, TimelineResponse


class TimelineBuilder:
    """Build timeline view from trace span tree."""

    def build(self, trace_id: uuid.UUID, span_tree: dict, started_at: datetime, completed_at: datetime | None) -> TimelineResponse:
        """Build timeline from span tree."""
        events: list[TimelineEvent] = []
        trace_start = started_at

        def _walk(span: dict, depth: int):
            span_started = span.get("started_at")
            if span_started:
                if isinstance(span_started, str):
                    span_started = datetime.fromisoformat(span_started.replace("Z", "+00:00"))
                start_ms = int((span_started - trace_start).total_seconds() * 1000)
            else:
                start_ms = 0

            label = self._make_label(span)
            events.append(TimelineEvent(
                span_id=span.get("id", ""),
                name=span.get("name", ""),
                span_type=span.get("span_type", ""),
                start_ms=max(0, start_ms),
                duration_ms=span.get("duration_ms", 0),
                depth=depth,
                status=span.get("status", "ok"),
                label=label,
            ))
            for child in span.get("children", []):
                _walk(child, depth + 1)

        if span_tree:
            _walk(span_tree, 0)

        events.sort(key=lambda e: e.start_ms)
        lanes = self._group_by_type(events)

        total_duration = 0
        if completed_at and started_at:
            total_duration = int((completed_at - started_at).total_seconds() * 1000)

        return TimelineResponse(
            trace_id=trace_id,
            total_duration_ms=total_duration,
            events=events,
            lanes=lanes,
        )

    def _make_label(self, span: dict) -> str:
        """Create human-readable label for span."""
        span_type = span.get("span_type", "")
        input_data = span.get("input_data", {})

        if span_type == "llm_call":
            model = input_data.get("model", "unknown")
            return f"LLM: {model}"
        elif span_type == "tool_call":
            tool = input_data.get("tool_name", "unknown")
            return f"Tool: {tool}"
        elif span_type == "retrieval":
            return f"Retrieval: {span.get('name', '')}"
        elif span_type == "memory_read":
            return f"Memory Read: {span.get('name', '')}"
        elif span_type == "memory_write":
            return f"Memory Write: {span.get('name', '')}"
        return span.get("name", "")

    def _group_by_type(self, events: list[TimelineEvent]) -> dict[str, list[TimelineEvent]]:
        """Group events by span_type into lanes."""
        lanes: dict[str, list[TimelineEvent]] = {}
        for e in events:
            lanes.setdefault(e.span_type, []).append(e)
        return lanes

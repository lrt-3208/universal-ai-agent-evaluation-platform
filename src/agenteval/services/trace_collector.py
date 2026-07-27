"""Trace Collector — basic trace collection and persistence

Reference: ../docs/phases/phase-3-runner.md §5
Phase 3 only collects basic Spans; Phase 5 extends to full Trace Tree.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

import structlog

logger = structlog.get_logger()


@dataclass
class SpanContext:
    """Context for an active span"""
    span_id: str
    trace_id: uuid.UUID
    parent_id: str | None


class TraceCollector:
    """Basic Trace collector.

    Collects spans during execution and builds a Trace entity.
    Runner creates TraceCollector per scenario execution.
    """

    def __init__(self, trace_id: uuid.UUID | None = None):
        self.trace_id = trace_id or uuid.uuid4()
        self.spans: list[dict] = []
        self._span_stack: list[SpanContext] = []

    def start_span(self, name: str, span_type: str, input_data: dict) -> SpanContext:
        """Start a new span and push to stack."""
        span_id = uuid.uuid4().hex
        parent_id = self._span_stack[-1].span_id if self._span_stack else None

        ctx = SpanContext(span_id=span_id, trace_id=self.trace_id, parent_id=parent_id)
        self._span_stack.append(ctx)

        span_data = {
            "id": span_id,
            "trace_id": str(self.trace_id),
            "parent_id": parent_id,
            "span_type": span_type,
            "name": name,
            "input_data": input_data,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
        }
        self.spans.append(span_data)
        logger.debug("trace.span_started", span_id=span_id, name=name, span_type=span_type)
        return ctx

    def end_span(self, ctx: SpanContext, output_data: dict, status: str = "ok"):
        """End an active span."""
        for span in self.spans:
            if span["id"] == ctx.span_id:
                completed_at = datetime.now(timezone.utc)
                started_at = datetime.fromisoformat(span["started_at"])
                span["completed_at"] = completed_at.isoformat()
                span["duration_ms"] = int((completed_at - started_at).total_seconds() * 1000)
                span["output_data"] = output_data
                span["status"] = status
                break

        if self._span_stack and self._span_stack[-1].span_id == ctx.span_id:
            self._span_stack.pop()

    def to_trace_data(self) -> dict:
        """Build trace data dict suitable for JSONB storage."""
        span_tree = self._build_tree()
        return {
            "trace_id": str(self.trace_id),
            "span_tree": span_tree,
            "span_count": len(self.spans),
            "total_llm_calls": sum(1 for s in self.spans if s["span_type"] == "llm_call"),
            "total_tool_calls": sum(1 for s in self.spans if s["span_type"] == "tool_call"),
            "total_tokens": self._sum_tokens(),
            "started_at": self.spans[0]["started_at"] if self.spans else datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _build_tree(self) -> dict:
        """Convert flat span list to nested tree structure."""
        span_map: dict[str, dict] = {}
        for s in self.spans:
            node = {**s, "children": []}
            span_map[s["id"]] = node

        root = None
        for s in self.spans:
            node = span_map[s["id"]]
            if s["parent_id"] is None:
                root = node
            elif s["parent_id"] in span_map:
                span_map[s["parent_id"]]["children"].append(node)

        return root or {
            "id": "root",
            "trace_id": str(self.trace_id),
            "parent_id": None,
            "span_type": "root",
            "name": "root",
            "input_data": {},
            "output_data": {},
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "duration_ms": 0,
            "status": "ok",
            "children": [],
        }

    def _sum_tokens(self) -> dict:
        """Sum tokens from all llm_call spans."""
        total_prompt = 0
        total_completion = 0
        for s in self.spans:
            if s["span_type"] == "llm_call" and "output_data" in s:
                tokens = s.get("output_data", {}).get("tokens", {})
                total_prompt += tokens.get("prompt", 0)
                total_completion += tokens.get("completion", 0)
        return {"prompt": total_prompt, "completion": total_completion}

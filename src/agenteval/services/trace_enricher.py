"""Trace Enricher — enrich span attributes.

Reference: ../docs/phases/phase-5-report.md §4.4
Adds: depth, self_time_ms, child_ratio, token attributes.
"""

from __future__ import annotations


class TraceEnricher:
    """Enrich trace spans with derived attributes."""

    def enrich(self, span_tree: dict) -> dict:
        """Enrich span tree in-place and return it."""
        if span_tree:
            self._enrich_span(span_tree, depth=0)
        return span_tree

    def _enrich_span(self, span: dict, depth: int):
        """Recursively enrich a span and its children."""
        span.setdefault("attributes", {})
        span["attributes"]["depth"] = depth

        children = span.get("children", [])
        duration_ms = span.get("duration_ms", 0)

        if children:
            child_duration = sum(c.get("duration_ms", 0) for c in children)
            span["attributes"]["child_duration_ms"] = child_duration
            span["attributes"]["self_time_ms"] = max(0, duration_ms - child_duration)
            span["attributes"]["child_ratio"] = round(
                child_duration / duration_ms, 4) if duration_ms > 0 else 0.0
        else:
            span["attributes"]["self_time_ms"] = duration_ms
            span["attributes"]["child_ratio"] = 0.0

        # LLM call token attributes
        if span.get("span_type") == "llm_call":
            tokens = span.get("output_data", {}).get("tokens", {})
            span["attributes"]["prompt_tokens"] = tokens.get("prompt", 0)
            span["attributes"]["completion_tokens"] = tokens.get("completion", 0)
            span["attributes"]["total_tokens"] = sum(tokens.values()) if tokens else 0

        # Tool call attributes
        if span.get("span_type") == "tool_call":
            span["attributes"]["tool_name"] = span.get("input_data", {}).get("tool_name", "unknown")
            span["attributes"]["tool_status"] = span.get("output_data", {}).get("status", "unknown")

        # Recurse children
        for child in children:
            self._enrich_span(child, depth + 1)

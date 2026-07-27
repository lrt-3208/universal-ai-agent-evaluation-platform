"""Global enums

Reference: ../contracts/domain-model.md §3
"""

from enum import Enum


class EvaluationStatus(str, Enum):
    """Evaluation lifecycle states"""
    PENDING = "pending"
    RUNNING = "running"
    SCORING = "scoring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScenarioExecutionStatus(str, Enum):
    """Individual scenario execution states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class JudgeType(str, Enum):
    """Judge implementation types"""
    RULE = "rule"
    LLM = "llm"
    EMBEDDING = "embedding"


class JudgeStatus(str, Enum):
    """Judge execution states"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AdapterType(str, Enum):
    """Agent adapter implementation types"""
    HTTP = "http"
    OPENAI = "openai"
    CUSTOM = "custom"


class TraceSpanType(str, Enum):
    """Trace span types"""
    ROOT = "root"
    LLM_CALL = "llm_call"
    TOOL_CALL = "tool_call"
    RETRIEVAL = "retrieval"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    REASONING = "reasoning"

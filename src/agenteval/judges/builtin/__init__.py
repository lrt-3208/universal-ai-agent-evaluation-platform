"""Built-in Judge implementations — auto-registration."""

from agenteval.judges import JudgeRegistry
from agenteval.judges.builtin.rule_judge import RuleJudge
from agenteval.judges.builtin.llm_judge import LLMJudge


def register_builtin_judges():
    """Register all built-in judges. Called at application startup."""
    JudgeRegistry.register("rule", RuleJudge)
    JudgeRegistry.register("llm", LLMJudge)
    # EmbeddingJudge: MAY — MVP not implemented, reserved for Plugin system

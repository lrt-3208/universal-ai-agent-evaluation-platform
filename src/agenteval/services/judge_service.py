"""Judge Service — scoring orchestration and config merge.

Reference: ../docs/phases/phase-4-judge.md §9
Orchestrates: load executions → resolve configs → run judges → aggregate → persist.
"""

import copy
import uuid
from dataclasses import asdict
from datetime import datetime, timezone

import structlog

from agenteval.judges import JudgeContext, JudgeOutput, JudgeRegistry, MetricScore
from agenteval.llm import LLMClientRegistry
from agenteval.services.score_aggregator import ScoreAggregator

logger = structlog.get_logger()


class JudgeService:
    """Judge scoring orchestrator.

    Responsibilities:
    1. Load completed ScenarioExecutions for an evaluation
    2. Resolve judge configs (scenario-level overrides evaluation-level)
    3. Execute each configured Judge
    4. Persist JudgeResult records
    5. Aggregate scores and update ScenarioExecution + Evaluation status
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self.aggregator = ScoreAggregator()

    async def judge_evaluation(self, evaluation_id: uuid.UUID):
        """Score all completed executions in an evaluation (background task)."""
        logger.info("judge_service.start", evaluation_id=str(evaluation_id))

        async with self.session_factory() as session:
            try:
                from agenteval.infra.repositories.evaluation_repo import EvaluationRepository
                from agenteval.infra.repositories.execution_repo import ScenarioExecutionRepository

                eval_repo = EvaluationRepository(session)
                evaluation = await eval_repo.get_by_id(evaluation_id)
                if not evaluation:
                    logger.error("judge_service.evaluation_not_found", evaluation_id=str(evaluation_id))
                    return

                exec_repo = ScenarioExecutionRepository(session)
                all_execs = await exec_repo.list_by_evaluation(evaluation_id)

                # Only score completed executions that haven't been scored yet
                completed_execs = [e for e in all_execs if e.status == "completed"]

                # Check which already have judge results (avoid lazy loading)
                from agenteval.infra.repositories.judge_result_repo import JudgeResultRepository
                judge_repo = JudgeResultRepository(session)

                for scenario_exec in completed_execs:
                    # Skip if already has judge results
                    existing = await judge_repo.list_by_scenario_execution(scenario_exec.id)
                    if existing:
                        continue
                    await self._judge_single(session, scenario_exec, evaluation)

                # Update evaluation status to COMPLETED
                await eval_repo.update_status(evaluation_id, "completed")
                await session.commit()

                logger.info("judge_service.completed", evaluation_id=str(evaluation_id),
                            scored=len(completed_execs))

            except Exception as e:
                logger.exception("judge_service.error", evaluation_id=str(evaluation_id), error=str(e))
                try:
                    from agenteval.infra.repositories.evaluation_repo import EvaluationRepository
                    eval_repo = EvaluationRepository(session)
                    await eval_repo.update_status(evaluation_id, "failed", f"Judge error: {e}")
                    await session.commit()
                except Exception:
                    logger.exception("judge_service.error_update_failed")

    async def _judge_single(self, session, scenario_exec, evaluation):
        """Score a single ScenarioExecution with all configured Judges."""
        from agenteval.infra.repositories.execution_repo import (
            AgentExecutionRepository, TraceRepository,
        )
        from agenteval.infra.repositories.judge_result_repo import JudgeResultRepository
        from agenteval.infra.repositories.scenario_repo import ScenarioRepository

        # Load related data
        ae_repo = AgentExecutionRepository(session)
        agent_exec = await ae_repo.get_by_scenario_execution(scenario_exec.id)
        if not agent_exec:
            logger.warning("judge_service.no_agent_execution",
                           scenario_exec_id=str(scenario_exec.id))
            return

        scenario_repo = ScenarioRepository(session)
        scenario = await scenario_repo.get_by_id(scenario_exec.scenario_id)
        if not scenario:
            logger.warning("judge_service.scenario_not_found",
                           scenario_id=str(scenario_exec.scenario_id))
            return

        trace = None
        if agent_exec.trace_id:
            trace_repo = TraceRepository(session)
            trace = await trace_repo.get_by_id(agent_exec.trace_id)

        # Resolve judge configs (scenario-level overrides evaluation-level)
        judge_configs = self._resolve_judge_configs(scenario, evaluation)

        if not judge_configs:
            logger.warning("judge_service.no_judge_configs",
                           evaluation_id=str(evaluation.id))
            return

        # Create LLM client if needed (lazy, shared across judges)
        llm_client = self._create_llm_client(judge_configs, evaluation)

        # Build context
        ctx = JudgeContext(
            scenario=scenario,
            agent_execution=agent_exec,
            trace=trace,
            config={},
            llm_client=llm_client,
        )

        # Execute each judge
        outputs: list[JudgeOutput] = []
        judge_result_repo = JudgeResultRepository(session)

        for jc in judge_configs:
            if not jc.get("enabled", True):
                continue

            judge_type = jc.get("judge_type", "")
            started_at = datetime.now(timezone.utc)

            try:
                judge = JudgeRegistry.create(judge_type)
                ctx.config = jc
                output = await judge.evaluate(ctx)
                outputs.append(output)

                # Persist JudgeResult
                await self._save_judge_result(
                    judge_result_repo, scenario_exec.id, jc, output, started_at
                )

            except Exception as e:
                logger.error("judge_service.judge_failed",
                             judge_type=judge_type,
                             scenario_exec_id=str(scenario_exec.id),
                             error=str(e))
                # Save failed result
                from agenteval.infra.models.judge_result_model import JudgeResultModel
                failed_result = JudgeResultModel(
                    scenario_execution_id=scenario_exec.id,
                    judge_type=judge_type,
                    judge_config=jc,
                    status="failed",
                    metric_scores=[],
                    started_at=started_at,
                    completed_at=datetime.now(timezone.utc),
                    error_message=str(e),
                )
                await judge_result_repo.create(failed_result)

        # Aggregate scores
        if outputs:
            weights = self._extract_global_weights(judge_configs)
            aggregated = self.aggregator.aggregate(outputs, weights)
            scenario_exec.overall_score = aggregated.overall_score
            scenario_exec.overall_verdict = aggregated.overall_verdict
        else:
            scenario_exec.overall_score = 0.0
            scenario_exec.overall_verdict = "fail"

        scenario_exec.updated_at = datetime.now(timezone.utc)
        await session.flush()

    def _resolve_judge_configs(self, scenario, evaluation) -> list[dict]:
        """Merge scenario-level and evaluation-level judge configs.

        Scenario-level judge_config overrides evaluation-level.
        """
        base_configs = copy.deepcopy(evaluation.judge_configs or [])
        scenario_override = scenario.judge_config

        if not scenario_override:
            return base_configs

        # Scenario-level override: merge same judge_type
        for sc in scenario_override.get("judges", []):
            found = False
            for bc in base_configs:
                if bc.get("judge_type") == sc.get("judge_type"):
                    bc.update(sc)  # Shallow merge
                    found = True
                    break
            if not found:
                base_configs.append(sc)

        # Apply scenario-level global weight overrides
        global_weights = scenario_override.get("weights", {})
        if global_weights:
            for bc in base_configs:
                bc.setdefault("weights", {}).update(global_weights)

        return base_configs

    def _create_llm_client(self, judge_configs: list[dict], evaluation):
        """Create LLM client if any judge requires it."""
        needs_llm = any(jc.get("judge_type") == "llm" for jc in judge_configs)
        if not needs_llm:
            return None

        # Get LLM config from evaluation config or judge config
        eval_config = evaluation.config or {}
        llm_config = eval_config.get("llm_judge", {})

        # Also check judge-level params
        for jc in judge_configs:
            if jc.get("judge_type") == "llm":
                params = jc.get("params", {})
                if params.get("api_key"):
                    llm_config.update(params)
                break

        # Fallback to default LLM config from Settings
        from agenteval.core.config import get_settings
        settings = get_settings()
        if not llm_config.get("api_key") and settings.llm_api_key:
            llm_config.setdefault("api_key", settings.llm_api_key)
        if not llm_config.get("base_url") and settings.llm_base_url:
            llm_config.setdefault("base_url", settings.llm_base_url)
        if not llm_config.get("default_model") and settings.llm_default_model:
            llm_config.setdefault("default_model", settings.llm_default_model)

        provider = llm_config.get("provider", settings.llm_provider or "openai")
        try:
            return LLMClientRegistry.create(provider, llm_config)
        except Exception as e:
            logger.warning("judge_service.llm_client_create_failed", error=str(e))
            return None

    def _extract_global_weights(self, judge_configs: list[dict]) -> dict[str, float]:
        """Extract global weight overrides from judge configs."""
        weights: dict[str, float] = {}
        for jc in judge_configs:
            weights.update(jc.get("weights", {}))
        return weights

    async def _save_judge_result(self, repo, scenario_exec_id, judge_config, output, started_at):
        """Persist a JudgeResult record."""
        from agenteval.infra.models.judge_result_model import JudgeResultModel

        # Serialize MetricScore list
        metric_scores_data = [asdict(ms) for ms in output.metric_scores]

        # Calculate per-judge overall score
        if output.metric_scores:
            total_w = sum(ms.weight for ms in output.metric_scores)
            overall = sum(ms.score * ms.weight for ms in output.metric_scores) / total_w if total_w > 0 else 0.0
            overall = round(max(0.0, min(1.0, overall)), 4)
        else:
            overall = None

        # Determine verdict for this judge
        verdict = None
        if overall is not None:
            if overall >= 0.8:
                verdict = "pass"
            elif overall >= 0.5:
                verdict = "partial"
            else:
                verdict = "fail"

        status = "failed" if output.error else "completed"

        result = JudgeResultModel(
            scenario_execution_id=scenario_exec_id,
            judge_type=output.judge_type,
            judge_config=judge_config,
            status=status,
            metric_scores=metric_scores_data,
            overall_score=overall,
            overall_verdict=verdict,
            reasoning=output.reasoning,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            error_message=output.error,
        )
        await repo.create(result)

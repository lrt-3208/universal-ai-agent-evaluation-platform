"""Evaluation Runner Orchestrator

Reference: ../docs/phases/phase-3-runner.md §6
Core engine that reads Scenarios, calls Adapter, collects Trace, produces AgentExecution.

Uses FastAPI BackgroundTasks for background execution (no Celery dependency for MVP).
"""

import asyncio
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.adapters import AdapterRegistry, AgentRequest, AgentResponse
from agenteval.core.exceptions import (
    AdapterError, AdapterTimeoutError, DatasetEmptyError,
    EvaluationNotFoundError, NotFoundException, UnsupportedAdapterError,
)
from agenteval.infra.models.agent_execution_model import AgentExecutionModel
from agenteval.infra.models.scenario_execution_model import ScenarioExecutionModel
from agenteval.infra.models.trace_model import TraceModel
from agenteval.infra.repositories.evaluation_repo import EvaluationRepository
from agenteval.infra.repositories.execution_repo import (
    AgentExecutionRepository, ScenarioExecutionRepository, TraceRepository,
)
from agenteval.infra.repositories.scenario_repo import ScenarioRepository
from agenteval.services.trace_collector import TraceCollector

logger = structlog.get_logger()


class EvaluationRunner:
    """Evaluation execution orchestrator.

    Manages: scenario loading, concurrent execution, retry/timeout, trace collection.
    """

    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def run_evaluation(self, evaluation_id: uuid.UUID):
        """Execute entire evaluation task (runs as background task)."""
        logger.info("runner.start", evaluation_id=str(evaluation_id))
        async with self.session_factory() as session:
            try:
                eval_repo = EvaluationRepository(session)
                evaluation = await eval_repo.get_by_id(evaluation_id)
                if not evaluation:
                    logger.error("evaluation.not_found", evaluation_id=str(evaluation_id))
                    return

                # Update status to RUNNING
                await eval_repo.update_status(evaluation_id, "running")
                await session.commit()

                # Load scenarios with optional filters
                scenario_repo = ScenarioRepository(session)
                config = evaluation.config or {}
                filter_tags = config.get("filter_tags", [])
                filter_priority_min = config.get("filter_priority_min", 0)

                scenarios, total = await scenario_repo.list_by_dataset(
                    dataset_id=evaluation.dataset_id,
                    page=1, page_size=10000,
                    tags=filter_tags if filter_tags else None,
                    priority_min=filter_priority_min if filter_priority_min > 0 else None,
                )

                if not scenarios:
                    await eval_repo.update_status(evaluation_id, "failed", "Dataset has no matching scenarios")
                    await session.commit()
                    return

                # Create ScenarioExecution records
                exec_repo = ScenarioExecutionRepository(session)
                exec_records = []
                for sc in scenarios:
                    rec = ScenarioExecutionModel(
                        evaluation_id=evaluation_id,
                        scenario_id=sc.id,
                        status="pending",
                    )
                    exec_records.append(rec)
                exec_records = await exec_repo.batch_create(exec_records)
                await session.commit()

                # Concurrent execution
                max_concurrent = config.get("max_concurrent", 10)
                semaphore = asyncio.Semaphore(max_concurrent)
                tasks = [
                    self._run_single(
                        exec_id=rec.id,
                        scenario_id=rec.scenario_id,
                        agent_config=evaluation.agent_config,
                        eval_config=config,
                        semaphore=semaphore,
                    )
                    for rec in exec_records
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Aggregate results
                failed_count = sum(1 for r in results if isinstance(r, Exception) or r is None)
                if failed_count == len(results):
                    await eval_repo.update_status(evaluation_id, "failed", "All scenarios failed")
                else:
                    await eval_repo.update_status(evaluation_id, "scoring")
                    await session.commit()

                    # Auto-judge if configured (Phase 4)
                    auto_judge = config.get("auto_judge", True)
                    if auto_judge and evaluation.judge_configs:
                        from agenteval.services.judge_service import JudgeService
                        judge_service = JudgeService(self.session_factory)
                        await judge_service.judge_evaluation(evaluation_id)
                        # judge_evaluation already commits and sets COMPLETED
                        logger.info("evaluation.judge_completed", evaluation_id=str(evaluation_id))
                        return
                    else:
                        # No judge configs or auto_judge disabled → mark completed
                        await eval_repo.update_status(evaluation_id, "completed")

                await session.commit()
                logger.info("evaluation.completed", evaluation_id=str(evaluation_id),
                            total=len(results), failed=failed_count)
            except Exception as e:
                logger.exception("evaluation.error", evaluation_id=str(evaluation_id), error=str(e))
                try:
                    eval_repo = EvaluationRepository(session)
                    await eval_repo.update_status(evaluation_id, "failed", str(e))
                    await session.commit()
                except Exception:
                    logger.exception("evaluation.error_update_failed")

    async def _run_single(
        self,
        exec_id: uuid.UUID,
        scenario_id: uuid.UUID,
        agent_config: dict,
        eval_config: dict,
        semaphore: asyncio.Semaphore,
    ):
        """Execute single scenario with semaphore control."""
        async with semaphore:
            async with self.session_factory() as session:
                try:
                    exec_repo = ScenarioExecutionRepository(session)
                    await exec_repo.update_status(exec_id, "running")

                    # Load scenario
                    scenario_repo = ScenarioRepository(session)
                    scenario = await scenario_repo.get_by_id(scenario_id)
                    if not scenario:
                        await exec_repo.update_status(exec_id, "failed", "Scenario not found")
                        await session.commit()
                        return None

                    # Execute
                    agent_execution = await self._execute_scenario(
                        scenario=scenario,
                        agent_config=agent_config,
                        eval_config=eval_config,
                        exec_id=exec_id,
                        session=session,
                    )

                    await exec_repo.update_status(exec_id, "completed", retry_count=agent_execution.retry_count)
                    await session.commit()
                    return agent_execution

                except (AdapterTimeoutError,) as e:
                    exec_repo = ScenarioExecutionRepository(session)
                    await exec_repo.update_status(exec_id, "timeout", str(e))
                    await session.commit()
                    return None
                except Exception as e:
                    logger.error("evaluation.scenario_failed", exec_id=str(exec_id), error=str(e))
                    exec_repo = ScenarioExecutionRepository(session)
                    await exec_repo.update_status(exec_id, "failed", str(e))
                    await session.commit()
                    return None

    async def _execute_scenario(
        self,
        scenario,
        agent_config: dict,
        eval_config: dict,
        exec_id: uuid.UUID,
        session: AsyncSession,
    ) -> AgentExecutionModel:
        """Execute single scenario: capability check + request build + trace wrap + retry."""
        adapter = AdapterRegistry.create(agent_config["adapter_type"], agent_config)

        trace_id = uuid.uuid4()
        trace_collector = TraceCollector(trace_id)

        # Root span
        root_span = trace_collector.start_span(
            f"scenario:{scenario.external_id}", "root",
            input_data={"scenario_id": str(scenario.id), "external_id": scenario.external_id})

        # Build messages based on capability
        if "stateful" in adapter.capabilities:
            messages = [{"role": "user", "content": scenario.input_data.get("user_message", "")}]
        else:
            messages = self._build_messages(scenario)

        agent_request = AgentRequest(
            messages=messages,
            system_prompt=agent_config.get("system_prompt"),
            tools=agent_config.get("tools") if "tools" in adapter.capabilities else None,
            temperature=agent_config.get("temperature", 0.7),
            max_tokens=agent_config.get("max_tokens", 4096),
            metadata={"memory": scenario.memory or {}, "context": scenario.input_data.get("context", {})},
        )

        # Trace wrap: adapter span
        adapter_span = trace_collector.start_span(
            f"adapter:{adapter.adapter_type}", "llm_call",
            input_data={
                "messages": agent_request.messages[:3],  # Snapshot (truncated for storage)
                "model": agent_config.get("model", ""),
                "adapter_type": adapter.adapter_type,
            })

        # Execute with retry
        max_retries = eval_config.get("retry_count", 2)
        retry_delay = eval_config.get("retry_delay_seconds", 5)
        timeout = eval_config.get("timeout_seconds", 120)
        started_at = datetime.now(timezone.utc)
        last_error = None
        attempt = 0
        agent_response = None

        for attempt in range(max_retries + 1):
            try:
                agent_response = await asyncio.wait_for(
                    adapter.execute(agent_request),
                    timeout=timeout,
                )
                trace_collector.end_span(adapter_span, output_data={
                    "final_message": agent_response.final_message[:200],
                    "tokens": agent_response.tokens,
                    "finish_reason": agent_response.finish_reason,
                }, status="ok")
                break
            except (AdapterTimeoutError, AdapterError) as e:
                last_error = e
                if attempt < max_retries:
                    logger.warning("adapter.retry", attempt=attempt + 1, max_retries=max_retries, error=str(e))
                    await asyncio.sleep(retry_delay * (attempt + 1))
                else:
                    trace_collector.end_span(adapter_span, output_data={"error": str(e)}, status="error")
                    raise
        else:
            raise last_error or AdapterError("Max retries exceeded")

        completed_at = datetime.now(timezone.utc)
        latency_ms = int((completed_at - started_at).total_seconds() * 1000)

        trace_collector.end_span(root_span, output_data={"status": "completed"}, status="ok")
        trace_data = trace_collector.to_trace_data()

        # Save Trace
        trace_repo = TraceRepository(session)
        trace_model = TraceModel(
            id=trace_id,
            span_tree=trace_data["span_tree"],
            span_count=trace_data["span_count"],
            total_llm_calls=trace_data["total_llm_calls"],
            total_tool_calls=trace_data["total_tool_calls"],
            total_tokens=trace_data["total_tokens"],
            started_at=datetime.fromisoformat(trace_data["started_at"]),
            completed_at=datetime.fromisoformat(trace_data["completed_at"]),
        )
        await trace_repo.create(trace_model)

        # Build conversation
        conversation_data = {
            "messages": self._build_conversation_messages(scenario, agent_response),
            "turn_count": len([m for m in messages if m["role"] == "user"]),
            "total_tokens": agent_response.tokens,
        }

        # Save AgentExecution
        ae_repo = AgentExecutionRepository(session)
        ae = AgentExecutionModel(
            scenario_execution_id=exec_id,
            agent_adapter_type=adapter.adapter_type,
            agent_config=agent_config,
            agent_version=agent_config.get("model", "unknown"),
            status="completed",
            conversation_data=conversation_data,
            trace_id=trace_id,
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=latency_ms,
            retry_count=attempt,
            cost_usd=agent_response.cost_usd,
        )
        await ae_repo.create(ae)
        await session.flush()

        return ae

    def _build_messages(self, scenario) -> list[dict]:
        """Build full message list from scenario (stateless)."""
        messages = list(scenario.history or [])
        messages.append({
            "role": "user",
            "content": scenario.input_data.get("user_message", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return messages

    def _build_conversation_messages(self, scenario, response: AgentResponse) -> list[dict]:
        """Build complete conversation messages."""
        messages = list(scenario.history or [])
        messages.append({"role": "user", "content": scenario.input_data.get("user_message", "")})
        messages.extend(response.messages)
        return messages

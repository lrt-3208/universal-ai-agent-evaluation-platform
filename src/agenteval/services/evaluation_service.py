"""Evaluation Service — business logic for evaluation CRUD and lifecycle

Reference: ../docs/phases/phase-3-runner.md §7
"""

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.adapters import AdapterRegistry
from agenteval.core.exceptions import (
    ConflictException, DatasetEmptyError, EvaluationNotFoundError,
    NotFoundException, UnsupportedAdapterError,
)
from agenteval.infra.models.evaluation_model import EvaluationModel
from agenteval.infra.repositories.dataset_repo import DatasetRepository
from agenteval.infra.repositories.evaluation_repo import EvaluationRepository
from agenteval.infra.repositories.execution_repo import ScenarioExecutionRepository
from agenteval.infra.repositories.scenario_repo import ScenarioRepository
from agenteval.schemas.evaluation import CreateEvaluationRequest

logger = structlog.get_logger()


class EvaluationService:
    """Evaluation business logic: create, query, cancel, status."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.eval_repo = EvaluationRepository(session)
        self.scenario_repo = ScenarioRepository(session)
        self.dataset_repo = DatasetRepository(session)
        self.exec_repo = ScenarioExecutionRepository(session)

    async def create_evaluation(
        self,
        project_id: uuid.UUID,
        request: CreateEvaluationRequest,
        created_by: str = "system",
    ) -> EvaluationModel:
        """Create evaluation and trigger background execution."""
        # Validate dataset exists
        dataset = await self.dataset_repo.get_by_id(request.dataset_id)
        if not dataset:
            raise NotFoundException(f"Dataset not found: {request.dataset_id}")

        # Validate dataset has scenarios
        scenarios, count = await self.scenario_repo.list_by_dataset(
            dataset_id=request.dataset_id, page=1, page_size=1)
        if count == 0:
            raise DatasetEmptyError(f"Dataset {request.dataset_id} has no scenarios")

        # Validate adapter type
        try:
            adapter_cls = AdapterRegistry.get_class(request.agent_config.get("adapter_type", ""))
        except KeyError:
            raise UnsupportedAdapterError(
                f"Unsupported adapter type: '{request.agent_config.get('adapter_type')}'. "
                f"Available: {AdapterRegistry.list_registered()}")

        # Create evaluation record
        evaluation = EvaluationModel(
            project_id=project_id,
            name=request.name,
            dataset_id=request.dataset_id,
            agent_config=request.agent_config,
            judge_configs=request.judge_configs,
            status="pending",
            config=request.config.model_dump(),
            version_label=request.version_label,
            created_by=created_by,
        )
        evaluation = await self.eval_repo.create(evaluation)
        await self.session.commit()

        logger.info("evaluation.created", evaluation_id=str(evaluation.id),
                     project_id=str(project_id), name=request.name)
        return evaluation

    async def get_evaluation(self, evaluation_id: uuid.UUID) -> EvaluationModel:
        evaluation = await self.eval_repo.get_by_id(evaluation_id)
        if not evaluation:
            raise EvaluationNotFoundError(f"Evaluation not found: {evaluation_id}")
        return evaluation

    async def list_evaluations(
        self,
        project_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[EvaluationModel], int]:
        return await self.eval_repo.list_by_project(project_id, page, page_size, status)

    async def cancel_evaluation(self, evaluation_id: uuid.UUID) -> EvaluationModel:
        """Cancel evaluation: mark pending scenarios as skipped."""
        evaluation = await self.get_evaluation(evaluation_id)
        if evaluation.status in ("completed", "failed", "cancelled"):
            raise ConflictException(f"Evaluation already in terminal state: {evaluation.status}")

        # Mark pending executions as skipped
        skip_count = await self.exec_repo.skip_pending(evaluation_id)

        # Update evaluation status
        evaluation = await self.eval_repo.update_status(evaluation_id, "cancelled")
        await self.session.commit()

        logger.info("evaluation.cancelled", evaluation_id=str(evaluation_id), skip_count=skip_count)
        return evaluation

    async def get_status(self, evaluation_id: uuid.UUID) -> dict:
        """Get evaluation status with execution counts."""
        evaluation = await self.get_evaluation(evaluation_id)
        execs = await self.exec_repo.list_by_evaluation(evaluation_id)
        counts: dict[str, int] = {}
        for e in execs:
            counts[e.status] = counts.get(e.status, 0) + 1

        return {
            "id": evaluation.id,
            "status": evaluation.status,
            "total_scenarios": len(execs),
            "completed": counts.get("completed", 0),
            "failed": counts.get("failed", 0),
            "timeout": counts.get("timeout", 0),
            "skipped": counts.get("skipped", 0),
            "pending": counts.get("pending", 0),
            "running": counts.get("running", 0),
        }

    async def get_executions(self, evaluation_id: uuid.UUID):
        """Get all scenario executions for an evaluation."""
        await self.get_evaluation(evaluation_id)  # Validate exists
        return await self.exec_repo.list_by_evaluation(evaluation_id)

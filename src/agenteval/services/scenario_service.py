"""Scenario service - business logic layer"""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.exceptions import ConflictException, NotFoundException
from agenteval.infra.models.scenario_model import ScenarioModel
from agenteval.infra.repositories.dataset_repo import DatasetRepository
from agenteval.infra.repositories.scenario_repo import ScenarioRepository
from agenteval.schemas.scenario import (
    CreateScenarioRequest,
    ScenarioBriefResponse,
    ScenarioResponse,
    UpdateScenarioRequest,
)

logger = structlog.get_logger()

MAX_SCENARIOS_PER_IMPORT = 5000


class ScenarioService:
    """Scenario business logic"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ScenarioRepository(session)
        self.dataset_repo = DatasetRepository(session)

    async def create(
        self, dataset_id: uuid.UUID, request: CreateScenarioRequest
    ) -> ScenarioResponse:
        """Create a single scenario"""
        dataset = await self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise NotFoundException(
                message=f"Dataset not found: {dataset_id}",
                code=40403,
            )

        # Check external_id uniqueness within dataset
        existing = await self.repo.get_by_dataset_and_external_id(
            dataset_id, request.external_id
        )
        if existing:
            raise ConflictException(
                message=f"Scenario external_id '{request.external_id}' already exists in dataset",
                code=40904,
            )

        scenario = ScenarioModel(
            dataset_id=dataset_id,
            external_id=request.external_id,
            title=request.title,
            description=request.description,
            input_data=request.input,
            history=request.history,
            memory=request.memory,
            expected=request.expected,
            constraints=request.constraints,
            judge_config=request.judge_config,
            tags=request.tags,
            priority=request.priority,
            metadata_=request.metadata,
            status="draft",
        )
        scenario = await self.repo.create(scenario)

        # Update dataset scenario_count
        count = await self.repo.count_by_dataset(dataset_id)
        await self.dataset_repo.update(dataset, scenario_count=count)

        logger.info(
            "scenario.created",
            scenario_id=str(scenario.id),
            dataset_id=str(dataset_id),
        )
        return ScenarioResponse.model_validate(scenario)

    async def batch_create(
        self, dataset_id: uuid.UUID, requests: list[CreateScenarioRequest]
    ) -> list[ScenarioResponse]:
        """Batch create scenarios (max 100)"""
        dataset = await self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise NotFoundException(
                message=f"Dataset not found: {dataset_id}",
                code=40403,
            )

        # Check for duplicate external_ids in the request
        ext_ids = [r.external_id for r in requests]
        seen = set()
        for eid in ext_ids:
            if eid in seen:
                raise ConflictException(
                    message=f"Duplicate external_id in batch: {eid}",
                    code=40904,
                )
            seen.add(eid)

        entities = []
        for req in requests:
            entities.append(
                ScenarioModel(
                    dataset_id=dataset_id,
                    external_id=req.external_id,
                    title=req.title,
                    description=req.description,
                    input_data=req.input,
                    history=req.history,
                    memory=req.memory,
                    expected=req.expected,
                    constraints=req.constraints,
                    judge_config=req.judge_config,
                    tags=req.tags,
                    priority=req.priority,
                    metadata_=req.metadata,
                    status="draft",
                )
            )

        created = await self.repo.batch_create(entities)

        # Update dataset scenario_count
        count = await self.repo.count_by_dataset(dataset_id)
        await self.dataset_repo.update(dataset, scenario_count=count)

        logger.info(
            "scenario.batch_created",
            dataset_id=str(dataset_id),
            count=len(created),
        )
        return [ScenarioResponse.model_validate(s) for s in created]

    async def get(self, scenario_id: uuid.UUID) -> ScenarioResponse:
        """Get scenario by ID"""
        scenario = await self.repo.get_by_id(scenario_id)
        if not scenario:
            raise NotFoundException(
                message=f"Scenario not found: {scenario_id}",
                code=40404,
            )
        return ScenarioResponse.model_validate(scenario)

    async def list_by_dataset(
        self,
        dataset_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        tags: str = "",
        status: str = "",
        priority_min: int = 0,
        search: str = "",
        sort: str = "-priority",
    ) -> tuple[list[ScenarioBriefResponse], int]:
        """List scenarios with advanced filtering"""
        dataset = await self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise NotFoundException(
                message=f"Dataset not found: {dataset_id}",
                code=40403,
            )

        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
        items, total = await self.repo.list_by_dataset(
            dataset_id=dataset_id,
            page=page,
            page_size=page_size,
            tags=tag_list,
            status=status or None,
            priority_min=priority_min,
            search=search,
            sort=sort,
        )
        briefs = [ScenarioBriefResponse.model_validate(s) for s in items]
        return briefs, total

    async def update(
        self, scenario_id: uuid.UUID, request: UpdateScenarioRequest
    ) -> ScenarioResponse:
        """Update scenario"""
        scenario = await self.repo.get_by_id(scenario_id)
        if not scenario:
            raise NotFoundException(
                message=f"Scenario not found: {scenario_id}",
                code=40404,
            )

        update_data = request.model_dump(exclude_unset=True)
        if "input" in update_data:
            update_data["input_data"] = update_data.pop("input")
        if "metadata" in update_data:
            update_data["metadata_"] = update_data.pop("metadata")

        scenario = await self.repo.update(scenario, **update_data)
        logger.info("scenario.updated", scenario_id=str(scenario_id))
        return ScenarioResponse.model_validate(scenario)

    async def delete(self, scenario_id: uuid.UUID) -> None:
        """Soft delete scenario"""
        scenario = await self.repo.get_by_id(scenario_id)
        if not scenario:
            raise NotFoundException(
                message=f"Scenario not found: {scenario_id}",
                code=40404,
            )

        dataset_id = scenario.dataset_id
        await self.repo.soft_delete(scenario_id)

        # Update dataset scenario_count
        dataset = await self.dataset_repo.get_by_id(dataset_id)
        if dataset:
            count = await self.repo.count_by_dataset(dataset_id)
            await self.dataset_repo.update(dataset, scenario_count=count)

        logger.info("scenario.deleted", scenario_id=str(scenario_id))

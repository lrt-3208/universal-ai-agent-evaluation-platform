"""Dataset service - business logic layer"""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.exceptions import ConflictException, NotFoundException
from agenteval.infra.models.dataset_model import DatasetModel
from agenteval.infra.repositories.dataset_repo import DatasetRepository
from agenteval.infra.repositories.project_repo import ProjectRepository
from agenteval.infra.repositories.scenario_repo import ScenarioRepository
from agenteval.schemas.dataset import (
    CreateDatasetRequest,
    DatasetBriefResponse,
    DatasetResponse,
    UpdateDatasetRequest,
)

logger = structlog.get_logger()


class DatasetService:
    """Dataset business logic"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = DatasetRepository(session)
        self.scenario_repo = ScenarioRepository(session)
        self.project_repo = ProjectRepository(session)

    async def create(
        self, project_id: uuid.UUID, request: CreateDatasetRequest
    ) -> DatasetResponse:
        """Create an empty dataset"""
        # Check project exists
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException(
                message=f"Project not found: {project_id}",
                code=40402,
            )

        # Check version uniqueness
        existing = await self.repo.get_by_project_name_version(
            project_id, request.name, request.version
        )
        if existing:
            raise ConflictException(
                message=f"Dataset {request.name} v{request.version} already exists",
                code=40903,
            )

        # Unset previous latest for same name
        await self.repo.unset_latest(project_id, request.name)

        dataset = DatasetModel(
            project_id=project_id,
            name=request.name,
            version=request.version,
            description=request.description,
            format="yaml",
            tags=request.tags,
            metadata_=request.metadata,
            is_latest=True,
        )
        dataset = await self.repo.create(dataset)
        logger.info(
            "dataset.created",
            dataset_id=str(dataset.id),
            project_id=str(project_id),
        )
        return DatasetResponse.model_validate(dataset)

    async def get(self, dataset_id: uuid.UUID) -> DatasetResponse:
        """Get dataset by ID"""
        dataset = await self.repo.get_by_id(dataset_id)
        if not dataset:
            raise NotFoundException(
                message=f"Dataset not found: {dataset_id}",
                code=40403,
            )
        return DatasetResponse.model_validate(dataset)

    async def list_by_project(
        self,
        project_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DatasetBriefResponse], int]:
        """List datasets in a project"""
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException(
                message=f"Project not found: {project_id}",
                code=40402,
            )

        datasets, total = await self.repo.list_by_project(
            project_id=project_id, page=page, page_size=page_size
        )
        briefs = [DatasetBriefResponse.model_validate(d) for d in datasets]
        return briefs, total

    async def update(
        self, dataset_id: uuid.UUID, request: UpdateDatasetRequest
    ) -> DatasetResponse:
        """Update dataset metadata"""
        dataset = await self.repo.get_by_id(dataset_id)
        if not dataset:
            raise NotFoundException(
                message=f"Dataset not found: {dataset_id}",
                code=40403,
            )

        update_data = request.model_dump(exclude_unset=True)
        if "metadata" in update_data:
            update_data["metadata_"] = update_data.pop("metadata")
        dataset = await self.repo.update(dataset, **update_data)
        logger.info("dataset.updated", dataset_id=str(dataset_id))
        return DatasetResponse.model_validate(dataset)

    async def delete(self, dataset_id: uuid.UUID) -> None:
        """Soft delete dataset (cascade scenarios)"""
        dataset = await self.repo.get_by_id(dataset_id)
        if not dataset:
            raise NotFoundException(
                message=f"Dataset not found: {dataset_id}",
                code=40403,
            )

        # Cascade soft delete scenarios
        await self.scenario_repo.soft_delete_by_dataset(dataset_id)
        await self.repo.soft_delete(dataset_id)
        logger.info("dataset.deleted", dataset_id=str(dataset_id))

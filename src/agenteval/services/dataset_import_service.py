"""Dataset Import/Export service

Reference: ../docs/phases/phase-2-scenario.md §5.1, §7.1
"""

import uuid
from io import StringIO

import structlog
import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from agenteval.core.exceptions import (
    ConflictException,
    DSLValidationError,
    NotFoundException,
    ValidationError,
)
from agenteval.infra.models.dataset_model import DatasetModel
from agenteval.infra.models.scenario_model import ScenarioModel
from agenteval.infra.repositories.dataset_repo import DatasetRepository
from agenteval.infra.repositories.project_repo import ProjectRepository
from agenteval.infra.repositories.scenario_repo import ScenarioRepository
from agenteval.schemas.dataset import DatasetResponse, ImportDatasetRequest
from agenteval.schemas.scenario import ValidationResultVO
from agenteval.services.dsl_parser import ScenarioEntity, get_parser
from agenteval.services.dsl_validator import DSLValidator

logger = structlog.get_logger()


class DatasetImportService:
    """Handle dataset import from DSL and export to DSL"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.dataset_repo = DatasetRepository(session)
        self.scenario_repo = ScenarioRepository(session)
        self.project_repo = ProjectRepository(session)
        self.validator = DSLValidator()

    async def validate_only(
        self, request: ImportDatasetRequest
    ) -> ValidationResultVO:
        """Validate DSL content without persisting"""
        return self.validator.validate(request.content, request.format)

    async def import_dataset(
        self, project_id: uuid.UUID, request: ImportDatasetRequest
    ) -> DatasetResponse:
        """Import dataset from DSL content"""
        # Check project exists
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise NotFoundException(
                message=f"Project not found: {project_id}",
                code=40402,
            )

        # Validate DSL
        validation = self.validator.validate(request.content, request.format)
        if not validation.valid:
            raise DSLValidationError(
                message="DSL validation failed",
                detail={
                    "errors": [e.model_dump() for e in validation.errors],
                    "warnings": validation.warnings,
                },
            )

        # Check version uniqueness
        existing = await self.dataset_repo.get_by_project_name_version(
            project_id, request.name, request.version
        )
        if existing:
            raise ConflictException(
                message=f"Dataset {request.name} v{request.version} already exists",
                code=40903,
            )

        # Parse DSL to get scenarios
        parser = get_parser(request.format)
        output = parser.parse(request.content)

        # Unset previous latest for same name
        await self.dataset_repo.unset_latest(project_id, request.name)

        # Create dataset
        dataset = DatasetModel(
            project_id=project_id,
            name=request.name,
            version=request.version,
            description=request.description,
            format=request.format,
            tags=request.tags,
            metadata_=request.metadata,
            is_latest=True,
            scenario_count=len(output.scenarios),
        )
        dataset = await self.dataset_repo.create(dataset)

        # Create scenarios
        if output.scenarios:
            entities = self._build_scenario_models(dataset.id, output.scenarios)
            await self.scenario_repo.batch_create(entities)

        logger.info(
            "dataset.imported",
            dataset_id=str(dataset.id),
            project_id=str(project_id),
            scenario_count=len(output.scenarios),
        )
        return DatasetResponse.model_validate(dataset)

    def _build_scenario_models(
        self, dataset_id: uuid.UUID, scenarios: list[ScenarioEntity]
    ) -> list[ScenarioModel]:
        """Convert parsed scenario entities to ORM models"""
        models = []
        for s in scenarios:
            models.append(
                ScenarioModel(
                    dataset_id=dataset_id,
                    external_id=s.external_id,
                    title=s.title,
                    description=s.description,
                    input_data=s.input_data,
                    history=s.history,
                    memory=s.memory,
                    expected=s.expected,
                    constraints=s.constraints,
                    judge_config=s.judge_config,
                    tags=s.tags,
                    priority=s.priority,
                    metadata_=s.metadata,
                    status=s.status,
                )
            )
        return models

    async def export_dataset(
        self, dataset_id: uuid.UUID, format: str = "yaml"
    ) -> str:
        """Export dataset as DSL content"""
        dataset = await self.dataset_repo.get_by_id(dataset_id)
        if not dataset:
            raise NotFoundException(
                message=f"Dataset not found: {dataset_id}",
                code=40403,
            )

        scenarios = await self.scenario_repo.list_all_by_dataset(dataset_id)

        # Build DSL structure
        dsl = {
            "dataset": {
                "name": dataset.name,
                "version": dataset.version,
                "description": dataset.description or "",
                "tags": dataset.tags or [],
                "metadata": getattr(dataset, "metadata_", dataset.__dict__.get("metadata", {})),
            },
            "scenarios": [],
        }

        for s in scenarios:
            scenario_dict = {
                "id": s.external_id,
                "title": s.title,
            }
            if s.description:
                scenario_dict["description"] = s.description
            if s.priority:
                scenario_dict["priority"] = s.priority
            if s.tags:
                scenario_dict["tags"] = s.tags
            if s.input_data:
                scenario_dict["input"] = s.input_data
            if s.history:
                scenario_dict["history"] = s.history
            if s.memory:
                scenario_dict["memory"] = s.memory
            if s.expected:
                scenario_dict["expected"] = s.expected
            if s.constraints:
                scenario_dict["constraints"] = s.constraints
            if s.judge_config:
                scenario_dict["judge_config"] = s.judge_config
            if getattr(s, "metadata_", s.__dict__.get("metadata", {})):
                scenario_dict["metadata"] = getattr(s, "metadata_", {})

            dsl["scenarios"].append(scenario_dict)

        if format == "json":
            import json
            return json.dumps(dsl, indent=2, ensure_ascii=False)

        # YAML output
        buf = StringIO()
        yaml.dump(dsl, buf, allow_unicode=True, default_flow_style=False, sort_keys=False)
        return buf.getvalue()

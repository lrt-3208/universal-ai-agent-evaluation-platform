"""Scenario system - datasets and scenarios tables

Revision ID: 002_scenario_system
Revises: 001_initial
Create Date: 2026-07-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "002_scenario_system"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Datasets table
    op.create_table(
        "datasets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("description", sa.String(512)),
        sa.Column("format", sa.String(16), nullable=False),
        sa.Column("source_uri", sa.String(512)),
        sa.Column("scenario_count", sa.Integer, server_default="0"),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("is_latest", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("project_id", "name", "version", name="uq_dataset_project_name_version"),
    )
    op.create_index("ix_datasets_project_id", "datasets", ["project_id"])
    op.create_index("ix_datasets_name", "datasets", ["name"])

    # Scenarios table
    op.create_table(
        "scenarios",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_id", UUID(as_uuid=True), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("input_data", JSONB, nullable=False),
        sa.Column("history", JSONB, server_default="[]"),
        sa.Column("memory", JSONB, server_default="{}"),
        sa.Column("expected", JSONB, server_default="{}"),
        sa.Column("constraints", JSONB, server_default="{}"),
        sa.Column("judge_config", JSONB),
        sa.Column("tags", JSONB, server_default="[]"),
        sa.Column("priority", sa.Integer, server_default="0"),
        sa.Column("metadata", JSONB, server_default="{}"),
        sa.Column("status", sa.String(16), server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("dataset_id", "external_id", name="uq_scenario_dataset_external_id"),
    )
    op.create_index("ix_scenarios_dataset_id", "scenarios", ["dataset_id"])

    # GIN indexes for JSONB queries
    op.execute("CREATE INDEX ix_scenarios_tags_gin ON scenarios USING GIN (tags)")
    op.execute("CREATE INDEX ix_scenarios_input_gin ON scenarios USING GIN (input_data jsonb_path_ops)")
    op.execute("CREATE INDEX ix_scenarios_expected_gin ON scenarios USING GIN (expected jsonb_path_ops)")

    # Partial index for paginated queries
    op.execute(
        "CREATE INDEX ix_scenarios_dataset_priority ON scenarios (dataset_id, priority DESC) "
        "WHERE deleted_at IS NULL"
    )


def downgrade() -> None:
    op.drop_table("scenarios")
    op.drop_table("datasets")

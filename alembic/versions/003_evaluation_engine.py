"""Evaluation engine - evaluations, scenario_executions, agent_executions, traces tables

Revision ID: 003_evaluation_engine
Revises: 002_scenario_system
Create Date: 2026-07-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "003_evaluation_engine"
down_revision: Union[str, None] = "002_scenario_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Evaluations table
    op.create_table(
        "evaluations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("dataset_id", UUID(as_uuid=True), sa.ForeignKey("datasets.id"), nullable=False),
        sa.Column("agent_config", JSONB, nullable=False),
        sa.Column("judge_configs", JSONB, nullable=False, server_default="[]"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("config", JSONB, nullable=False, server_default="{}"),
        sa.Column("version_label", sa.String(64)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        sa.Column("created_by", sa.String(128), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("project_id", "name", "version_label", name="uq_evaluation_project_name_version"),
    )
    op.create_index("ix_evaluations_project_id", "evaluations", ["project_id"])
    op.create_index("ix_evaluations_dataset_id", "evaluations", ["dataset_id"])
    op.create_index("ix_evaluations_status", "evaluations", ["status"])

    # Scenario executions table
    op.create_table(
        "scenario_executions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("evaluation_id", UUID(as_uuid=True), sa.ForeignKey("evaluations.id"), nullable=False),
        sa.Column("scenario_id", UUID(as_uuid=True), sa.ForeignKey("scenarios.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("overall_score", sa.Float),
        sa.Column("overall_verdict", sa.String(16)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_scenario_exec_evaluation_status", "scenario_executions",
                    ["evaluation_id", "status"])
    op.create_index("ix_scenario_exec_scenario_id", "scenario_executions", ["scenario_id"])

    # Traces table (before agent_executions since agent_executions.trace_id → traces.id)
    op.create_table(
        "traces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("span_tree", JSONB, nullable=False),
        sa.Column("span_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_llm_calls", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_tool_calls", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_tokens", JSONB, nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )

    # Agent executions table
    op.create_table(
        "agent_executions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_execution_id", UUID(as_uuid=True),
                  sa.ForeignKey("scenario_executions.id"), nullable=False, unique=True),
        sa.Column("agent_adapter_type", sa.String(16), nullable=False),
        sa.Column("agent_config", JSONB, nullable=False),
        sa.Column("agent_version", sa.String(64)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("conversation_data", JSONB),
        sa.Column("trace_id", UUID(as_uuid=True), sa.ForeignKey("traces.id")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("latency_ms", sa.Integer),
        sa.Column("error_message", sa.Text),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("traces")
    op.drop_table("agent_executions")
    op.drop_table("scenario_executions")
    op.drop_table("evaluations")

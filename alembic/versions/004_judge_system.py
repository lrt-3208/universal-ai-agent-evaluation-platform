"""Judge system - judge_results table

Revision ID: 004_judge_system
Revises: 003_evaluation_engine
Create Date: 2026-07-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "004_judge_system"
down_revision: Union[str, None] = "003_evaluation_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "judge_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("scenario_execution_id", UUID(as_uuid=True),
                  sa.ForeignKey("scenario_executions.id"), nullable=False),
        sa.Column("judge_type", sa.String(16), nullable=False),
        sa.Column("judge_config", JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("metric_scores", JSONB, nullable=False, server_default="[]"),
        sa.Column("overall_score", sa.Float),
        sa.Column("overall_verdict", sa.String(16)),
        sa.Column("reasoning", sa.Text),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_judge_results_scenario_exec_id", "judge_results",
                    ["scenario_execution_id"])
    op.create_index("ix_judge_results_status", "judge_results", ["status"])


def downgrade() -> None:
    op.drop_table("judge_results")

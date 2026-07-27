"""Regression system - regressions table

Revision ID: 006_regression_system
Revises: 005_report_system
Create Date: 2026-07-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "006_regression_system"
down_revision: Union[str, None] = "005_report_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regressions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True),
                  sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("baseline_evaluation_id", UUID(as_uuid=True),
                  sa.ForeignKey("evaluations.id"), nullable=False),
        sa.Column("target_evaluation_id", UUID(as_uuid=True),
                  sa.ForeignKey("evaluations.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("scenario_diffs", JSONB),
        sa.Column("metric_diffs", JSONB),
        sa.Column("overall_verdict", sa.String(16)),
        sa.Column("summary", JSONB),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_regressions_project_id", "regressions", ["project_id"])
    op.create_index("ix_regressions_status", "regressions", ["status"])
    op.create_index("ix_regressions_baseline_eval", "regressions", ["baseline_evaluation_id"])
    op.create_index("ix_regressions_target_eval", "regressions", ["target_evaluation_id"])


def downgrade() -> None:
    op.drop_table("regressions")

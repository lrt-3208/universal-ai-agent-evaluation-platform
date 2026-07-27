"""Report system - reports table

Revision ID: 005_report_system
Revises: 004_judge_system
Create Date: 2026-07-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "005_report_system"
down_revision: Union[str, None] = "004_judge_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("evaluation_id", UUID(as_uuid=True),
                  sa.ForeignKey("evaluations.id"), nullable=False),
        sa.Column("format", sa.String(16), nullable=False),  # json | html
        sa.Column("status", sa.String(16), nullable=False, server_default="generating"),
        sa.Column("content_uri", sa.Text),
        sa.Column("content", sa.Text),  # Inline content for MVP
        sa.Column("summary", JSONB),
        sa.Column("metrics_snapshot", JSONB),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_reports_evaluation_id", "reports", ["evaluation_id"])
    op.create_index("ix_reports_status", "reports", ["status"])


def downgrade() -> None:
    op.drop_table("reports")

"""Plugin system - plugins table

Revision ID: 007_plugin_system
Revises: 006_regression_system
Create Date: 2026-07-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "007_plugin_system"
down_revision: Union[str, None] = "006_regression_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plugins",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("description", sa.String(512)),
        sa.Column("author", sa.String(128)),
        sa.Column("entry_point", sa.String(256), nullable=False),
        sa.Column("config_schema", JSONB, server_default="{}"),
        sa.Column("config", JSONB, server_default="{}"),
        sa.Column("status", sa.String(16), server_default="disabled"),
        sa.Column("error_message", sa.Text),
        sa.Column("manifest_path", sa.String(512)),
        sa.Column("loaded_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_plugins_type", "plugins", ["type"])
    op.create_index("ix_plugins_status", "plugins", ["status"])


def downgrade() -> None:
    op.drop_index("ix_plugins_status", table_name="plugins")
    op.drop_index("ix_plugins_type", table_name="plugins")
    op.drop_table("plugins")

"""add saved cubes

Revision ID: j5k6l7m8n9o0
Revises: 94a9e82e9a1e
Create Date: 2026-09-17 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "j5k6l7m8n9o0"
down_revision: Union[str, None] = "94a9e82e9a1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_cube",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("query_definition", postgresql.JSONB(), nullable=False),
        sa.Column("output_table", sa.String(), nullable=False, unique=True),
        sa.Column("refresh_schedule", sa.String(), nullable=True),
        sa.Column("last_refreshed_at", sa.String(), nullable=True),
    )
    op.create_index("ix_saved_cube_project_id", "saved_cube", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_saved_cube_project_id", table_name="saved_cube")
    op.drop_table("saved_cube")
"""add semantic model tables

Revision ID: h4i5j6k7l8m9
Revises: g3h4i5j6k7l8
Create Date: 2026-09-06 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h4i5j6k7l8m9"
down_revision: Union[str, tuple[str, str], None] = ("7df350d88391", "01ac329e92ad")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "semantic_table",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("connection_id", sa.Integer(), sa.ForeignKey("connection.id"), nullable=False),
        sa.Column("physical_table", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_semantic_table_project_id", "semantic_table", ["project_id"])
    op.create_index("ix_semantic_table_connection_id", "semantic_table", ["connection_id"])

    op.create_table(
        "semantic_field",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("semantic_table_id", sa.Integer(), sa.ForeignKey("semantic_table.id"), nullable=False),
        sa.Column("column_name", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("field_type", sa.String(), nullable=False),
        sa.Column("data_type", sa.String(), nullable=False),
        sa.Column("default_aggregation", sa.String(), nullable=True),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_semantic_field_semantic_table_id", "semantic_field", ["semantic_table_id"])

    op.create_table(
        "semantic_relationship",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("from_table_id", sa.Integer(), sa.ForeignKey("semantic_table.id"), nullable=False),
        sa.Column("from_column", sa.String(), nullable=False),
        sa.Column("to_table_id", sa.Integer(), sa.ForeignKey("semantic_table.id"), nullable=False),
        sa.Column("to_column", sa.String(), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=False, server_default="many_to_one"),
    )
    op.create_index("ix_semantic_relationship_project_id", "semantic_relationship", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_semantic_relationship_project_id", table_name="semantic_relationship")
    op.drop_table("semantic_relationship")
    op.drop_index("ix_semantic_field_semantic_table_id", table_name="semantic_field")
    op.drop_table("semantic_field")
    op.drop_index("ix_semantic_table_connection_id", table_name="semantic_table")
    op.drop_index("ix_semantic_table_project_id", table_name="semantic_table")
    op.drop_table("semantic_table")
"""encrypt connection configs

Revision ID: a1b2c3d4e5f6
Revises: bcba7fa8edc5
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "bcba7fa8edc5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "connection",
        "source_connection_json",
        existing_type=sa.JSON(),
        type_=sa.String(),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        "connection",
        "destination_connection_json",
        existing_type=sa.JSON(),
        type_=sa.String(),
        existing_nullable=True,
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "connection",
        "source_connection_json",
        existing_type=sa.String(),
        type_=sa.JSON(),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        "connection",
        "destination_connection_json",
        existing_type=sa.String(),
        type_=sa.JSON(),
        existing_nullable=False,
        nullable=True,
    )

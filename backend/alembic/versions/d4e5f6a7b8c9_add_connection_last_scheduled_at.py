"""add last_scheduled_at to connection

Revision ID: d4e5f6a7b8c9
Revises: c1a2b3d4e5f6
Create Date: 2026-08-16 12:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c1a2b3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('connection', sa.Column('last_scheduled_at', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('connection', 'last_scheduled_at')

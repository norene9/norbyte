"""add sync state

Revision ID: c1a2b3d4e5f6
Revises: 9f8b7c6d5e4
Create Date: 2026-08-16 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, None] = '9f8b7c6d5e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table('sync_state'):
        op.create_table(
            'sync_state',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('connection_id', sa.Integer(), nullable=False),
            sa.Column('table_name', sa.String(), nullable=False),
            sa.Column('cursor_field', sa.String(), nullable=True),
            sa.Column('cursor_value', sa.String(), nullable=True),
        )


def downgrade() -> None:
    op.drop_table('sync_state')

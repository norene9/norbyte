"""merge heads

Revision ID: 7df350d88391
Revises: d4e5f6a7b8c9, g3h4i5j6k7l8
Create Date: 2026-09-06 11:36:13.562222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7df350d88391'
down_revision: Union[str, None] = ('d4e5f6a7b8c9', 'g3h4i5j6k7l8')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

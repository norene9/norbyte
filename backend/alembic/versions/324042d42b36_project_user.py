"""project_user

Revision ID: 324042d42b36
Revises: 0e5c4a0d8cb6
Create Date: 2026-08-07 23:27:23.571269

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '324042d42b36'
down_revision: Union[str, None] = '0e5c4a0d8cb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""backfill destination_table_prefix for existing connections

Revision ID: g3h4i5j6k7l8
Revises: f2g3h4i5j6k7
Create Date: 2026-09-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g3h4i5j6k7l8'
down_revision: Union[str, None] = 'f2g3h4i5j6k7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfill destination_table_prefix for all existing connections that don't have one
    # Use the connection ID to generate a unique prefix like "conn3_" for connection ID 3
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE connection
            SET destination_table_prefix = 'conn' || id || '_'
            WHERE destination_table_prefix IS NULL
            """
        )
    )


def downgrade() -> None:
    # Clear the destination_table_prefix for all rows during downgrade
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE connection
            SET destination_table_prefix = NULL
            """
        )
    )

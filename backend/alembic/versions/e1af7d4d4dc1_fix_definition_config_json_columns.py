"""fix definition config_json columns

Revision ID: e1af7d4d4dc1
Revises: b06098e86f84
Create Date: 2026-08-05 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e1af7d4d4dc1"
down_revision: Union[str, None] = "b06098e86f84"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in ("source_definition", "destination_definition"):
        columns = {column["name"] for column in inspector.get_columns(table_name)}

        if "config_json" not in columns:
            op.add_column(table_name, sa.Column("config_json", sa.JSON(), nullable=True))

        if "config_icon" in columns:
            op.drop_column(table_name, "config_icon")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in ("source_definition", "destination_definition"):
        columns = {column["name"] for column in inspector.get_columns(table_name)}

        if "config_icon" not in columns:
            op.add_column(table_name, sa.Column("config_icon", sa.VARCHAR(), autoincrement=False, nullable=True))

        if "config_json" in columns:
            op.drop_column(table_name, "config_json")

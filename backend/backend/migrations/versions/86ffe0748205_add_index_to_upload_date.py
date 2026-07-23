"""Add index to upload_date

Revision ID: 86ffe0748205
Revises: 4bbdfe85b4e6
Create Date: 2026-07-06 12:09:37.459170

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '86ffe0748205'
down_revision: Union[str, None] = '4bbdfe85b4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

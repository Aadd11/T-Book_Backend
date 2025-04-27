"""Initial tables

Revision ID: 83b887301cca
Revises: d4b47cf318dc
Create Date: 2025-04-27 00:45:43.019702

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '83b887301cca'
down_revision: Union[str, None] = 'd4b47cf318dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

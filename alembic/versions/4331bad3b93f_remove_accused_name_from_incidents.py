"""Remove accused_name from Incidents

Revision ID: 4331bad3b93f
Revises: 458f0e4773ab
Create Date: 2023-11-30 19:01:11.728819

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4331bad3b93f'
down_revision: Union[str, None] = '458f0e4773ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('incidents', 'accused_name')


def downgrade() -> None:
    op.add_column('incidents', sa.Column('accused_name', sa.VARCHAR(), autoincrement=False, nullable=True))


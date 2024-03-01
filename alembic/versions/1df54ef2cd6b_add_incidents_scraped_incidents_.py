"""add incidents_scraped & incidents_verified to Article model

Revision ID: 1df54ef2cd6b
Revises: 8eebbabe396f
Create Date: 2024-02-29 19:04:19.368107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1df54ef2cd6b'
down_revision: Union[str, None] = '8eebbabe396f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('article', sa.Column('incidents_scraped', sa.Boolean(), nullable=True))
    op.add_column('article', sa.Column('incidents_verified', sa.Boolean(), nullable=True))
    pass


def downgrade() -> None:
    op.drop_column('article', 'incidents_verified')
    op.drop_column('article', 'incidents_scraped')
    pass

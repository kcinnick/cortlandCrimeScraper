"""add spellchecked_charges column

Revision ID: f3c912bf06cd
Revises: 1df54ef2cd6b
Create Date: 2024-03-20 15:26:16.872226

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3c912bf06cd'
down_revision: Union[str, None] = '1df54ef2cd6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('incident', sa.Column('spellchecked_charges', sa.VARCHAR(), nullable=True))
    pass


def downgrade() -> None:
    op.drop_column('incident', sa.Column('spellchecked_charges', sa.VARCHAR(), nullable=True))
    pass

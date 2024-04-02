"""Add Charges.category

Revision ID: d82ac6136b34
Revises: f3c912bf06cd
Create Date: 2024-04-01 13:24:39.496047

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd82ac6136b34'
down_revision: Union[str, None] = 'f3c912bf06cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('charges', sa.Column('category', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    op.drop_column('charges', 'category')
    # ### end Alembic commands ###


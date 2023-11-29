"""Initial migration

Revision ID: 04544a509ebc
Revises: 
Create Date: 2023-11-28 16:56:31.543781

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '04544a509ebc'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('combined_incidents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('incident_reported_date', sa.Date(), nullable=True),
    sa.Column('incident_date', sa.Date(), nullable=True),
    sa.Column('accused_name', sa.String(), nullable=True),
    sa.Column('accused_age', sa.Integer(), nullable=True),
    sa.Column('accused_location', sa.String(), nullable=True),
    sa.Column('charges', sa.String(), nullable=True),
    sa.Column('details', sa.String(), nullable=True),
    sa.Column('legal_actions', sa.String(), nullable=True),
    sa.Column('incident_location', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_unique_constraint(None, 'article', ['url'], schema='public')
    op.execute('ALTER TABLE incidents ALTER COLUMN incident_date TYPE date USING incident_date::date')
    op.alter_column('incidents', 'incident_date',
               existing_type=sa.TEXT(),
               type_=sa.Date(),
               existing_nullable=True)
    op.alter_column('incidents', 'incident_location',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('incidents', 'incident_location_lat',
               existing_type=sa.NUMERIC(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('incidents', 'incident_location_lng',
               existing_type=sa.NUMERIC(),
               type_=sa.String(),
               existing_nullable=True)
    op.drop_constraint('incidents_article_id_fkey', 'incidents', type_='foreignkey')
    op.create_foreign_key(None, 'incidents', 'article', ['article_id'], ['id'], source_schema='public', referent_schema='public')
    op.alter_column('incidents_from_pdf', 'incident_location',
               existing_type=sa.TEXT(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('incidents_from_pdf', 'incident_location_lat',
               existing_type=sa.NUMERIC(),
               type_=sa.String(),
               existing_nullable=True)
    op.alter_column('incidents_from_pdf', 'incident_location_lng',
               existing_type=sa.NUMERIC(),
               type_=sa.String(),
               existing_nullable=True)
    op.drop_constraint('incidents_with_errors_article_id_fkey', 'incidents_with_errors', type_='foreignkey')
    op.create_foreign_key(None, 'incidents_with_errors', 'article', ['article_id'], ['id'], source_schema='public', referent_schema='public')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'incidents_with_errors', schema='public', type_='foreignkey')
    op.execute('ALTER TABLE incidents ALTER COLUMN incident_date TYPE date USING incident_date::date')
    op.create_foreign_key('incidents_with_errors_article_id_fkey', 'incidents_with_errors', 'article', ['article_id'], ['id'])
    op.alter_column('incidents_from_pdf', 'incident_location_lng',
               existing_type=sa.String(),
               type_=sa.NUMERIC(),
               existing_nullable=True)
    op.alter_column('incidents_from_pdf', 'incident_location_lat',
               existing_type=sa.String(),
               type_=sa.NUMERIC(),
               existing_nullable=True)
    op.alter_column('incidents_from_pdf', 'incident_location',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.drop_constraint(None, 'incidents', schema='public', type_='foreignkey')
    op.create_foreign_key('incidents_article_id_fkey', 'incidents', 'article', ['article_id'], ['id'])
    op.alter_column('incidents', 'incident_location_lng',
               existing_type=sa.String(),
               type_=sa.NUMERIC(),
               existing_nullable=True)
    op.alter_column('incidents', 'incident_location_lat',
               existing_type=sa.String(),
               type_=sa.NUMERIC(),
               existing_nullable=True)
    op.alter_column('incidents', 'incident_location',
               existing_type=sa.String(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.alter_column('incidents', 'incident_date',
               existing_type=sa.Date(),
               type_=sa.TEXT(),
               existing_nullable=True)
    op.drop_constraint(None, 'article', schema='public', type_='unique')
    op.drop_table('combined_incidents')
    # ### end Alembic commands ###
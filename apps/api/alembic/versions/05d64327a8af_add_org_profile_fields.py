"""add_org_profile_fields

Revision ID: 05d64327a8af
Revises: 0d8359fffbeb
Create Date: 2026-08-07 20:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = '05d64327a8af'
down_revision = '0d8359fffbeb'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('organisations', sa.Column('gstin',   sa.String(20),  nullable=True))
    op.add_column('organisations', sa.Column('address', sa.String(500), nullable=True))
    op.add_column('organisations', sa.Column('phone',   sa.String(20),  nullable=True))
    op.add_column('organisations', sa.Column('website', sa.String(255), nullable=True))

def downgrade():
    op.drop_column('organisations', 'website')
    op.drop_column('organisations', 'phone')
    op.drop_column('organisations', 'address')
    op.drop_column('organisations', 'gstin')

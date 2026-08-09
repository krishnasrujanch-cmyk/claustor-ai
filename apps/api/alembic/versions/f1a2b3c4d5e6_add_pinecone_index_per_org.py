"""add_pinecone_index_per_org

Revision ID: f1a2b3c4d5e6
Revises: e8842ea9c078
Create Date: 2026-08-09
"""
from alembic import op
import sqlalchemy as sa

revision = 'f1a2b3c4d5e6'
down_revision = 'e8842ea9c078'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('organisations',
        sa.Column('pinecone_index', sa.String(100), nullable=True))

def downgrade():
    op.drop_column('organisations', 'pinecone_index')

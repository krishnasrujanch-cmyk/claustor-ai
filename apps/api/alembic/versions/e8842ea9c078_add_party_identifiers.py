"""add_party_identifiers

Revision ID: e8842ea9c078
Revises: 05d64327a8af
Create Date: 2026-08-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'e8842ea9c078'
down_revision = '05d64327a8af'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('contracts',
        sa.Column('party_identifiers', JSONB, nullable=True, server_default='[]'))

def downgrade():
    op.drop_column('contracts', 'party_identifiers')

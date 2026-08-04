"""add_contract_chunks_table

Revision ID: 0d8359fffbeb
Revises: 647ec462b04a
Create Date: 2026-08-03 21:30:20.652363
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0d8359fffbeb'
down_revision: Union[str, None] = '647ec462b04a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'contract_chunks',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('contract_id', sa.UUID(), nullable=False),
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.Column('is_parent', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('chunk_type', sa.String(20), server_default='clause', nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('heading', sa.String(500), nullable=True),
        sa.Column('section_ref', sa.String(100), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('importance', sa.String(10), nullable=True),
        sa.Column('cross_refs', postgresql.JSONB(), server_default='[]', nullable=True),
        sa.Column('table_json', postgresql.JSONB(), nullable=True),
        sa.Column('pinecone_id', sa.String(200), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['contract_id'], ['contracts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    # Indexes
    op.create_index('idx_chunks_contract', 'contract_chunks', ['contract_id'])
    op.create_index('idx_chunks_org', 'contract_chunks', ['org_id'])
    op.create_index('idx_chunks_parent', 'contract_chunks', ['parent_id'])
    op.create_index('idx_chunks_type', 'contract_chunks', ['chunk_type'])
    op.create_index('idx_chunks_pinecone', 'contract_chunks', ['pinecone_id'])
    # GIN index for BM25 full-text search
    op.execute("""
        CREATE INDEX idx_chunks_fts ON contract_chunks
        USING GIN (to_tsvector('english', text))
    """)


def downgrade() -> None:
    op.drop_index('idx_chunks_fts', table_name='contract_chunks')
    op.drop_index('idx_chunks_pinecone', table_name='contract_chunks')
    op.drop_index('idx_chunks_type', table_name='contract_chunks')
    op.drop_index('idx_chunks_parent', table_name='contract_chunks')
    op.drop_index('idx_chunks_org', table_name='contract_chunks')
    op.drop_index('idx_chunks_contract', table_name='contract_chunks')
    op.drop_table('contract_chunks')

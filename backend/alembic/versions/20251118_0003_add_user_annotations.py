"""add user annotations table

Revision ID: 20251118_0003
Revises: 20251005_0002
Create Date: 2025-11-18
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251118_0003'
down_revision = '20251005_0002'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_annotations table
    op.create_table('user_annotations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('image_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('annotation_type', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['image_id'], ['data_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_annotations_created_by_id'), 'user_annotations', ['created_by_id'], unique=False)
    op.create_index(op.f('ix_user_annotations_image_id'), 'user_annotations', ['image_id'], unique=False)


def downgrade():
    # Drop user_annotations table
    op.drop_index(op.f('ix_user_annotations_image_id'), table_name='user_annotations')
    op.drop_index(op.f('ix_user_annotations_created_by_id'), table_name='user_annotations')
    op.drop_table('user_annotations')

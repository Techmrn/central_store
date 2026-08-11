"""create_unserviceable_materials_table

Revision ID: 9a8b7c6d5e4f
Revises: 7ba67cd08ee5
Create Date: 2026-08-11 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a8b7c6d5e4f'
down_revision: Union[str, Sequence[str], None] = '7ba67cd08ee5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE assetmovementtype ADD VALUE IF NOT EXISTS 'UNSERVICEABLE'")
    op.execute("ALTER TYPE assetmovementtype ADD VALUE IF NOT EXISTS 'REPAIR'")
    op.execute("ALTER TYPE assetmovementtype ADD VALUE IF NOT EXISTS 'CONDEMNATION'")
    op.execute("ALTER TYPE assetmovementtype ADD VALUE IF NOT EXISTS 'DISPOSAL'")

    op.create_table(

        'unserviceable_materials',
        sa.Column('financial_year_id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('office_id', sa.Integer(), nullable=False),
        sa.Column('section_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('UNSERVICEABLE', 'UNDER_REPAIR', 'REPAIRED', 'CONDEMNED', 'DISPOSED', name='unserviceablestatus'), nullable=False),
        sa.Column('date_reported', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('reference_no', sa.String(length=100), nullable=True),
        sa.Column('remarks', sa.String(length=500), nullable=True),
        sa.Column('reported_by_id', sa.Integer(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['financial_year_id'], ['financial_years.id'], ),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ),
        sa.ForeignKeyConstraint(['office_id'], ['offices.id'], ),
        sa.ForeignKeyConstraint(['reported_by_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['section_id'], ['sections.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_unserviceable_materials_financial_year_id'), 'unserviceable_materials', ['financial_year_id'], unique=False)
    op.create_index(op.f('ix_unserviceable_materials_id'), 'unserviceable_materials', ['id'], unique=False)
    op.create_index(op.f('ix_unserviceable_materials_item_id'), 'unserviceable_materials', ['item_id'], unique=False)
    op.create_index(op.f('ix_unserviceable_materials_office_id'), 'unserviceable_materials', ['office_id'], unique=False)
    op.create_index(op.f('ix_unserviceable_materials_section_id'), 'unserviceable_materials', ['section_id'], unique=False)
    op.create_index(op.f('ix_unserviceable_materials_status'), 'unserviceable_materials', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_unserviceable_materials_status'), table_name='unserviceable_materials')
    op.drop_index(op.f('ix_unserviceable_materials_section_id'), table_name='unserviceable_materials')
    op.drop_index(op.f('ix_unserviceable_materials_office_id'), table_name='unserviceable_materials')
    op.drop_index(op.f('ix_unserviceable_materials_item_id'), table_name='unserviceable_materials')
    op.drop_index(op.f('ix_unserviceable_materials_id'), table_name='unserviceable_materials')
    op.drop_index(op.f('ix_unserviceable_materials_financial_year_id'), table_name='unserviceable_materials')
    op.drop_table('unserviceable_materials')

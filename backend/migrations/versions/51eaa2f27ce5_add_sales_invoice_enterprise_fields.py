"""add_sales_invoice_enterprise_fields

Revision ID: 51eaa2f27ce5
Revises: 86ffe0748205
Create Date: 2026-07-21 14:25:35.345240

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51eaa2f27ce5'
down_revision: Union[str, None] = '86ffe0748205'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sales_invoices', sa.Column('work_type', sa.String(), nullable=True))
    op.add_column('sales_invoices', sa.Column('description_work_details', sa.String(), nullable=True))
    op.add_column('sales_invoices', sa.Column('quantity', sa.Float(), nullable=True))
    op.add_column('sales_invoices', sa.Column('unit', sa.String(), nullable=True))
    op.add_column('sales_invoices', sa.Column('rate', sa.Float(), nullable=True))
    op.add_column('sales_invoices', sa.Column('remarks', sa.String(), nullable=True))
    op.add_column('sales_invoices', sa.Column('payment_date', sa.Date(), nullable=True))
    op.add_column('sales_invoices', sa.Column('payment_mode', sa.String(), nullable=True))
    op.add_column('sales_invoices', sa.Column('transaction_reference', sa.String(), nullable=True))
    op.create_index(op.f('ix_sales_invoices_work_type'), 'sales_invoices', ['work_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_sales_invoices_work_type'), table_name='sales_invoices')
    op.drop_column('sales_invoices', 'transaction_reference')
    op.drop_column('sales_invoices', 'payment_mode')
    op.drop_column('sales_invoices', 'payment_date')
    op.drop_column('sales_invoices', 'remarks')
    op.drop_column('sales_invoices', 'rate')
    op.drop_column('sales_invoices', 'unit')
    op.drop_column('sales_invoices', 'quantity')
    op.drop_column('sales_invoices', 'description_work_details')
    op.drop_column('sales_invoices', 'work_type')

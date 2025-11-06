"""Add purchase_date to holdings

Revision ID: 20251004_02_add_purchase_date
Revises: 20251004_01_add_transactions
Create Date: 2025-10-04

"""

from alembic import op
import sqlalchemy as sa


revision = "20251004_02_add_purchase_date"
down_revision = "20251004_01_add_transactions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "holdings",
        sa.Column("purchase_date", sa.Date(), nullable=True),
    )
    op.execute("UPDATE holdings SET purchase_date = DATE(created_at)")
    op.alter_column("holdings", "purchase_date", nullable=True)


def downgrade():
    op.drop_column("holdings", "purchase_date")

"""Add quote columns to assets

Revision ID: 20251004_03_add_quote_columns
Revises: 20251004_02_add_purchase_date
Create Date: 2025-10-04

"""

from alembic import op
import sqlalchemy as sa


revision = "20251004_03_add_quote_columns"
down_revision = "20251004_02_add_purchase_date"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("assets", sa.Column("last_quote_price", sa.Float(), nullable=True))
    op.add_column(
        "assets",
        sa.Column("last_quote_at", sa.DateTime(timezone=False), nullable=True),
    )


def downgrade():
    op.drop_column("assets", "last_quote_at")
    op.drop_column("assets", "last_quote_price")

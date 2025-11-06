"""Add transactions table

Revision ID: 20251004_01_add_transactions
Revises: 20250918_01_core
Create Date: 2025-10-04

"""

from alembic import op
import sqlalchemy as sa

revision = "20251004_01_add_transactions"
down_revision = "20250918_01_core"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "portfolio_id",
            sa.Integer(),
            sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            sa.Integer(),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("total", sa.Float(), nullable=False),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_transactions_portfolio", "transactions", ["portfolio_id"])
    op.create_index("ix_transactions_asset", "transactions", ["asset_id"])
    op.create_index("ix_transactions_executed", "transactions", ["executed_at"])


def downgrade():
    op.drop_index("ix_transactions_executed", table_name="transactions")
    op.drop_index("ix_transactions_asset", table_name="transactions")
    op.drop_index("ix_transactions_portfolio", table_name="transactions")
    op.drop_table("transactions")

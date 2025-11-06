"""Extend transactions with status, kind, metadata columns.

Revision ID: 20251030_05_extend_transactions_fields
Revises: 20251030_04_update_holdings
Create Date: 2025-10-30
"""

from alembic import op
import sqlalchemy as sa


revision = "20251030_05_extend_transactions"
down_revision = "20251030_04_update_holdings"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "transactions",
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
    )
    op.add_column(
        "transactions",
        sa.Column("kind", sa.String(), nullable=False, server_default="trade"),
    )
    op.add_column(
        "transactions",
        sa.Column("source", sa.String(), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column(
            "reversal_of_id",
            sa.Integer(),
            sa.ForeignKey("transactions.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_transactions_status_kind",
        "transactions",
        ["status", "kind"],
    )
    op.create_index(
        "ix_transactions_reversal_of",
        "transactions",
        ["reversal_of_id"],
    )

    op.execute(
        "UPDATE transactions SET status = 'active', kind = 'trade' WHERE status IS NULL OR kind IS NULL"
    )
    op.alter_column("transactions", "status", server_default=None)
    op.alter_column("transactions", "kind", server_default=None)


def downgrade():
    op.drop_index("ix_transactions_reversal_of", table_name="transactions")
    op.drop_index("ix_transactions_status_kind", table_name="transactions")
    op.drop_column("transactions", "reversal_of_id")
    op.drop_column("transactions", "note")
    op.drop_column("transactions", "source")
    op.drop_column("transactions", "kind")
    op.drop_column("transactions", "status")

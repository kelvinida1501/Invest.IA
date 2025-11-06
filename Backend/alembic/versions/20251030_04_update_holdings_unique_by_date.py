"""Update holdings unique constraint to include purchase_date

Revision ID: 20251030_04_update_holdings_unique_by_date
Revises: 20251004_03_add_asset_quote_columns
Create Date: 2025-10-30

"""

from alembic import op
import sqlalchemy as sa


revision = "20251030_04_update_holdings"
down_revision = "20251004_03_add_quote_columns"
branch_labels = None
depends_on = None


def upgrade():
    # Remove antiga unicidade por (portfolio_id, asset_id)
    try:
        op.drop_constraint(
            "uq_holdings_portfolio_asset", "holdings", type_="unique"
        )
    except Exception:
        # Em alguns bancos/estados pode já não existir
        pass

    # Garante coluna purchase_date existente (caso migrações fora de ordem)
    # op.add_column é idempotente somente se verificar previamente; aqui assumimos que já existe.

    # Cria nova unicidade por (portfolio_id, asset_id, purchase_date)
    op.create_unique_constraint(
        "uq_holdings_portfolio_asset_date",
        "holdings",
        ["portfolio_id", "asset_id", "purchase_date"],
    )


def downgrade():
    try:
        op.drop_constraint(
            "uq_holdings_portfolio_asset_date", "holdings", type_="unique"
        )
    except Exception:
        pass

    op.create_unique_constraint(
        "uq_holdings_portfolio_asset", "holdings", ["portfolio_id", "asset_id"]
    )


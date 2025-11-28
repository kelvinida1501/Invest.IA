"""Add quote columns to assets

Revision ID: 20251004_03_add_quote_columns
Revises: 20251004_02_add_purchase_date
Create Date: 2025-10-04

"""

# flake8: noqa

from alembic import op
import sqlalchemy as sa


revision = "20251004_03_add_quote_columns"
down_revision = "20251004_02_add_purchase_date"
branch_labels = None
depends_on = None


def upgrade():
    # Já incluído na revisão inicial (20250918_01_core). Evita erro de coluna duplicada.
    pass


def downgrade():
    pass

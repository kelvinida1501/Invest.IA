"""Add purchase_date to holdings

Revision ID: 20251004_02_add_purchase_date
Revises: 20251004_01_add_transactions
Create Date: 2025-10-04

"""
# flake8: noqa

from alembic import op
import sqlalchemy as sa


revision = "20251004_02_add_purchase_date"
down_revision = "20251004_01_add_transactions"
branch_labels = None
depends_on = None


def upgrade():
    # Já incluído na revisão inicial (20250918_01_core). Evita erro de coluna duplicada.
    pass


def downgrade():
    pass

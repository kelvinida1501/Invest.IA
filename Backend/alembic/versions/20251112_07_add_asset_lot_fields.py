"""Add lot/step metadata to assets.

Revision ID: 20251112_07_add_asset_lot_fields
Revises: 20251031_06_expand_risk_profile
Create Date: 2025-11-12
"""

from alembic import op
import sqlalchemy as sa


revision = "20251112_07_add_asset_lot_fields"
down_revision = "20251031_06_expand_risk_profile"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "assets",
        sa.Column("lot_size", sa.Float(), nullable=False, server_default="1.0"),
    )
    op.add_column(
        "assets",
        sa.Column("qty_step", sa.Float(), nullable=False, server_default="1.0"),
    )
    op.add_column(
        "assets",
        sa.Column(
            "supports_fractional",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.execute("UPDATE assets SET lot_size = 1.0 WHERE lot_size IS NULL")
    op.execute("UPDATE assets SET qty_step = 1.0 WHERE qty_step IS NULL")
    op.execute(
        "UPDATE assets SET supports_fractional = TRUE WHERE supports_fractional IS NULL"
    )
    op.alter_column("assets", "lot_size", server_default=None)
    op.alter_column("assets", "qty_step", server_default=None)
    op.alter_column("assets", "supports_fractional", server_default=None)


def downgrade():
    op.drop_column("assets", "supports_fractional")
    op.drop_column("assets", "qty_step")
    op.drop_column("assets", "lot_size")

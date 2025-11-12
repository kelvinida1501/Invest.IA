"""Expand risk profile table with answers and version metadata.

Revision ID: 20251031_06_expand_risk_profile
Revises: 20251030_05_extend_transactions
Create Date: 2025-10-31
"""

from alembic import op
import sqlalchemy as sa


revision = "20251031_06_expand_risk_profile"
down_revision = "20251030_05_extend_transactions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("risk_profiles", sa.Column("answers", sa.Text(), nullable=True))
    op.add_column(
        "risk_profiles", sa.Column("questionnaire_version", sa.String(), nullable=True)
    )
    op.add_column(
        "risk_profiles", sa.Column("score_version", sa.String(), nullable=True)
    )
    op.add_column("risk_profiles", sa.Column("rules", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("risk_profiles", "rules")
    op.drop_column("risk_profiles", "score_version")
    op.drop_column("risk_profiles", "questionnaire_version")
    op.drop_column("risk_profiles", "answers")

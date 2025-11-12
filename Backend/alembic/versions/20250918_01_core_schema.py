"""Core schema: users, assets, portfolios, holdings, prices, news, risk, chat

Revision ID: 20250918_01_core
Revises: <COLOQUE_AQUI_O_HEAD_ATUAL_OU_USE_None>
Create Date: 2025-09-18

"""

from alembic import op
import sqlalchemy as sa

# --- Ajuste aqui conforme seu histórico:
revision = "20250918_01_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # USERS
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=False), server_default=sa.text("NOW()")
        ),
    )

    # ASSETS (cadastro)
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(), nullable=False, unique=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("class_", sa.String(), nullable=True),  # acao|fundo|cripto|...
        sa.Column("currency", sa.String(), nullable=False, server_default="BRL"),
        sa.Column("last_quote_price", sa.Float(), nullable=True),
        sa.Column(
            "last_quote_at",
            sa.DateTime(timezone=False),
            nullable=True,
        ),
    )

    # PORTFOLIOS (permitindo mais de um por usuário; no MVP use 1 padrão)
    op.create_table(
        "portfolios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=False), server_default=sa.text("NOW()")
        ),
    )
    op.create_index("ix_portfolios_user", "portfolios", ["user_id"])

    # HOLDINGS (posições do usuário)
    op.create_table(
        "holdings",
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
            sa.ForeignKey("assets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("avg_price", sa.Float(), nullable=False),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=False), server_default=sa.text("NOW()")
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=False), server_default=sa.text("NOW()")
        ),
        sa.UniqueConstraint(
            "portfolio_id", "asset_id", name="uq_holdings_portfolio_asset"
        ),
    )
    op.create_index("ix_holdings_portfolio", "holdings", ["portfolio_id"])
    op.create_index("ix_holdings_asset", "holdings", ["asset_id"])

    # ASSET PRICES (série temporal para gráficos)
    op.create_table(
        "asset_prices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "asset_id",
            sa.Integer(),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=True),
        sa.Column("high", sa.Float(), nullable=True),
        sa.Column("low", sa.Float(), nullable=True),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=True),
        sa.UniqueConstraint("asset_id", "date", name="uq_asset_prices_asset_date"),
    )
    op.create_index("ix_asset_prices_asset_date", "asset_prices", ["asset_id", "date"])

    # NEWS (feed de notícias)
    op.create_table(
        "news_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False, unique=True),
        sa.Column("published_at", sa.DateTime(timezone=False), nullable=False),
        sa.Column("sentiment", sa.String(), nullable=True),
        # opcional futuro: tickers_relacionados JSONB
    )
    op.create_index("ix_news_published_at", "news_items", ["published_at"])

    # RISK PROFILE
    op.create_table(
        "risk_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "profile", sa.String(), nullable=False
        ),  # conservador|moderado|arrojado
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "last_updated", sa.DateTime(timezone=False), server_default=sa.text("NOW()")
        ),
    )

    # CHAT (sessões/mensagens)
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=False), server_default=sa.text("NOW()")
        ),
    )
    op.create_index("ix_chat_sessions_user", "chat_sessions", ["user_id"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Integer(),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(), nullable=False),  # user|assistant|system
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=False), server_default=sa.text("NOW()")
        ),
    )
    op.create_index(
        "ix_chat_messages_session_created",
        "chat_messages",
        ["session_id", "created_at"],
    )


def downgrade():
    op.drop_index("ix_chat_messages_session_created", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_user", table_name="chat_sessions")
    op.drop_table("chat_sessions")
    op.drop_table("risk_profiles")
    op.drop_index("ix_news_published_at", table_name="news_items")
    op.drop_table("news_items")
    op.drop_index("ix_asset_prices_asset_date", table_name="asset_prices")
    op.drop_table("asset_prices")
    op.drop_index("ix_holdings_asset", table_name="holdings")
    op.drop_index("ix_holdings_portfolio", table_name="holdings")
    op.drop_table("holdings")
    op.drop_index("ix_portfolios_user", table_name="portfolios")
    op.drop_table("portfolios")
    op.drop_table("assets")
    op.drop_table("users")

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Date,
    ForeignKey,
    Text,
    UniqueConstraint,
    Boolean,
)
from sqlalchemy.orm import relationship
from .base import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    portfolios = relationship(
        "Portfolio", back_populates="user", cascade="all, delete-orphan"
    )
    risk_profile = relationship(
        "RiskProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    chat_sessions = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )


class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    class_ = Column(String)  # acao|fundo|cripto|etf|...
    currency = Column(String, default="BRL")
    last_quote_price = Column(Float, nullable=True)
    last_quote_at = Column(DateTime, nullable=True)
    lot_size = Column(Float, nullable=False, default=1.0)
    qty_step = Column(Float, nullable=False, default=1.0)
    supports_fractional = Column(Boolean, nullable=False, default=True)

    prices = relationship(
        "AssetPrice", back_populates="asset", cascade="all, delete-orphan"
    )


class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="portfolios")
    holdings = relationship(
        "Holding", back_populates="portfolio", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="portfolio", cascade="all, delete-orphan"
    )


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (
        # Unicidade por ativo dentro do portfólio na mesma data de compra
        UniqueConstraint(
            "portfolio_id",
            "asset_id",
            "purchase_date",
            name="uq_holdings_portfolio_asset_date",
        ),
    )
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="CASCADE"))
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="RESTRICT"))
    quantity = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    purchase_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    portfolio = relationship("Portfolio", back_populates="holdings")
    asset = relationship("Asset")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(
        Integer, ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False
    )
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    type = Column(String, nullable=False)  # buy|sell
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    executed_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    status = Column(String, nullable=False, default="active")
    kind = Column(String, nullable=False, default="trade")  # trade|adjust|manual
    source = Column(String, nullable=True)  # auto|manual|import
    note = Column(Text, nullable=True)
    reversal_of_id = Column(Integer, ForeignKey("transactions.id", ondelete="SET NULL"))

    portfolio = relationship("Portfolio", back_populates="transactions")
    asset = relationship("Asset")
    reversal_of = relationship(
        "Transaction",
        remote_side=[id],
        backref="reversals",
        foreign_keys=[reversal_of_id],
    )


class AssetPrice(Base):
    __tablename__ = "asset_prices"
    id = Column(Integer, primary_key=True)
    asset_id = Column(
        Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float, nullable=False)
    volume = Column(Float)

    asset = relationship("Asset", back_populates="prices")


class NewsItem(Base):
    __tablename__ = "news_items"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True)
    published_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )
    sentiment = Column(String, nullable=True)


class RiskProfile(Base):
    __tablename__ = "risk_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    profile = Column(String, nullable=False)  # conservador|moderado|arrojado
    score = Column(Integer, nullable=False)
    last_updated = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    answers = Column(Text, nullable=True)
    questionnaire_version = Column(String, nullable=True)
    score_version = Column(String, nullable=True)
    rules = Column(Text, nullable=True)

    user = relationship("User", back_populates="risk_profile")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True)
    session_id = Column(
        Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String, nullable=False)  # user|assistant|system
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("ChatSession", back_populates="messages")

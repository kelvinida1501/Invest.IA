from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import yfinance as yf
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.models import Asset, AssetPrice


class QuoteNotFoundError(Exception):
    """Raised when no quote is available for a symbol."""


QUOTE_TTL = timedelta(minutes=5)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fetch_latest_quote(symbol: str) -> tuple[float, datetime, Optional[str]]:
    """
    Retrieve the latest available quote for the given Yahoo Finance symbol.

    Returns (price, retrieved_at, currency) where retrieved_at is naive UTC datetime.
    Raises QuoteNotFoundError if the symbol cannot be resolved or price missing.
    """
    ticker = yf.Ticker(symbol)

    price: Optional[float] = None
    currency: Optional[str] = None

    fast_info = getattr(ticker, "fast_info", None)
    if fast_info:
        price = fast_info.get("last_price") or fast_info.get("last_close")
        currency = fast_info.get("currency") or currency

    if price is None:
        try:
            history = ticker.history(period="1d", interval="1m")
        except Exception as exc:  # pragma: no cover
            raise QuoteNotFoundError(symbol) from exc
        if not history.empty:
            price = float(history["Close"].iloc[-1])

    if currency is None:
        info = getattr(ticker, "info", {}) or {}
        currency = info.get("currency") or currency

    if price is None:
        raise QuoteNotFoundError(symbol)

    return (
        float(price),
        _now_utc(),
        currency.upper() if isinstance(currency, str) else None,
    )


def _upsert_price_row(
    db: Session, asset_id: int, retrieved_at: datetime, price: float
) -> None:
    row = (
        db.query(AssetPrice)
        .filter(
            and_(
                AssetPrice.asset_id == asset_id, AssetPrice.date == retrieved_at.date()
            )
        )
        .first()
    )
    if row:
        row.close = price
    else:
        db.add(AssetPrice(asset_id=asset_id, date=retrieved_at.date(), close=price))


def needs_refresh(asset: Asset, force: bool = False) -> bool:
    if force:
        return True
    if asset.last_quote_at is None:
        return True
    return datetime.utcnow() - asset.last_quote_at > QUOTE_TTL


def refresh_asset_quote(db: Session, asset: Asset, *, force: bool = False) -> bool:
    """
    Refresh the stored quote for an asset if needed.
    Returns True when a new fetch was performed.
    """
    if not needs_refresh(asset, force=force):
        return False

    price, retrieved_at, currency = fetch_latest_quote(asset.symbol)
    asset.last_quote_price = price
    asset.last_quote_at = retrieved_at
    if currency:
        asset.currency = currency
    _upsert_price_row(db, asset.id, retrieved_at, price)
    return True

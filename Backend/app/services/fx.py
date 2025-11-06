from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Tuple

import yfinance as yf

logger = logging.getLogger(__name__)

_FX_CACHE: Dict[str, Tuple[float, float, datetime]] = {}
_FX_TTL_SECONDS = 5 * 60  # 5 minutes


class FxRateNotFoundError(Exception):
    """Raised when an FX rate cannot be retrieved."""


def _cache_key(base: str, quote: str) -> str:
    return f"{base.upper()}:{quote.upper()}"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_fx_rate(base: str, quote: str) -> Tuple[float, datetime]:
    """
    Returns the conversion rate to convert 1 unit of `base` into `quote`.
    """
    base = base.upper()
    quote = quote.upper()
    if base == quote:
        return 1.0, _now_utc()

    key = _cache_key(base, quote)
    cached = _FX_CACHE.get(key)
    now_ts = time.time()
    if cached:
        rate, cached_ts, ts = cached
        if now_ts - cached_ts <= _FX_TTL_SECONDS:
            return rate, ts

    ticker_symbol = f"{base}{quote}=X"
    ticker = yf.Ticker(ticker_symbol)
    rate = None

    fast_info = getattr(ticker, "fast_info", None)
    if fast_info:
        rate = fast_info.get("last_price") or fast_info.get("last_close")

    if rate is None:
        try:
            history = ticker.history(period="1d", interval="1m")
        except Exception as exc:  # pragma: no cover
            raise FxRateNotFoundError(ticker_symbol) from exc
        if not history.empty:
            rate = float(history["Close"].iloc[-1])

    if rate is None:
        raise FxRateNotFoundError(ticker_symbol)

    retrieved_at = _now_utc()
    _FX_CACHE[key] = (float(rate), now_ts, retrieved_at)
    return float(rate), retrieved_at

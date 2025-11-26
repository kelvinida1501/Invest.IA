from datetime import datetime, timedelta

import pytest

from app.services import quotes
from app.db.models import Asset


class DummySeries:
    def __getitem__(self, idx):
        return 7.0

    @property
    def iloc(self):
        return [7.0]


class DummyHistory:
    empty = False

    def __getitem__(self, key):
        return DummySeries()


class DummyTicker:
    def __init__(self):
        self.fast_info = {}
        self.info = {"currency": "usd"}

    def history(self, *args, **kwargs):
        return DummyHistory()


def test_fetch_latest_quote_uses_history(monkeypatch):
    monkeypatch.setattr(quotes, "yf", type("yf", (), {"Ticker": lambda symbol: DummyTicker()}))
    price, ts, currency = quotes.fetch_latest_quote("DUMMY")
    assert price == 7.0
    assert currency == "USD"
    assert isinstance(ts, datetime)


def test_needs_refresh_ttl(monkeypatch):
    asset = Asset(symbol="TTL", name="TTL", class_="acao", currency="BRL")
    fixed_now = datetime(2024, 1, 1, 12, 0)
    asset.last_quote_at = fixed_now

    monkeypatch.setattr(
        quotes, "_now_utc", lambda: fixed_now + timedelta(minutes=4)
    )
    assert quotes.needs_refresh(asset) is False

    monkeypatch.setattr(quotes, "_now_utc", lambda: fixed_now + timedelta(minutes=6))
    assert quotes.needs_refresh(asset) is True

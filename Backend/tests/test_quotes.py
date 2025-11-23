from datetime import datetime

from app.db.models import Asset, AssetPrice
from app.services import quotes


def test_refresh_asset_quote_uses_fetch_and_upserts(db_session, monkeypatch):
    asset = Asset(symbol="AAPL", name="Apple", class_="acao", currency="USD")
    db_session.add(asset)
    db_session.commit()

    fake_now = datetime(2024, 1, 1, 12, 0)

    def fake_fetch_latest_quote(symbol: str):
        return 123.45, fake_now, "usd"

    monkeypatch.setattr(quotes, "fetch_latest_quote", fake_fetch_latest_quote)

    refreshed = quotes.refresh_asset_quote(db_session, asset, force=True)
    db_session.commit()

    assert refreshed is True
    assert asset.last_quote_price == 123.45
    assert asset.currency == "USD"
    price_rows = db_session.query(AssetPrice).all()
    assert len(price_rows) == 1
    assert price_rows[0].close == 123.45
    assert price_rows[0].date == fake_now.date()


def test_needs_refresh_respects_ttl(monkeypatch):
    asset = Asset(symbol="MSFT", name="MSFT", class_="acao", currency="USD")
    now = datetime(2024, 1, 1, 12, 0)
    asset.last_quote_at = now

    monkeypatch.setattr(quotes, "datetime", type("dt", (), {"utcnow": lambda: now}))
    assert quotes.needs_refresh(asset, force=False) is False
    assert quotes.needs_refresh(asset, force=True) is True

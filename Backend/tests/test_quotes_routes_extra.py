from datetime import datetime

from app.routes import prices as prices_route
from app.db.models import Asset


def test_refresh_quotes_missing_asset_returns_404(client, user_token):
    headers, _ = user_token
    resp = client.post(
        "/api/prices/refresh",
        headers=headers,
        json={"symbols": ["MISSING"], "force": True},
    )
    assert resp.status_code == 404


def test_serialize_quote_converts_currency(monkeypatch):
    asset = Asset(symbol="USD1", name="Usd Asset", class_="acao", currency="USD")
    asset.last_quote_price = 10.0
    asset.last_quote_at = datetime(2024, 1, 1, 12, 0)

    def fake_get_fx(base, quote):
        return 5.0, datetime(2024, 1, 1, 12, 0)

    monkeypatch.setattr(prices_route, "get_fx_rate", fake_get_fx)
    payload = prices_route._serialize_quote(asset)
    assert payload["price"] == 50.0
    assert payload["currency"] == "USD"

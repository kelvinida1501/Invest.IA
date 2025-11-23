from datetime import date

from app.routes import prices as prices_route


def test_upsert_daily_creates_price(client, user_token):
    headers, _ = user_token
    # create asset first
    client.post(
        "/api/assets",
        headers=headers,
        json={"symbol": "NEW4", "name": "New Asset"},
    )
    resp = client.post(
        "/api/prices/upsert",
        headers=headers,
        json={"symbol": "NEW4", "date": "2024-01-01", "close": 12.34},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["symbol"] == "NEW4"
    assert body["close"] == 12.34
    assert body["date"] == "2024-01-01"


def test_refresh_quotes_uses_mock_refresh(client, user_token, monkeypatch):
    headers, _ = user_token
    called = {"count": 0}

    def fake_refresh(db, asset, force=False):
        called["count"] += 1
        asset.last_quote_price = 10.0
        return True

    def fake_get_fx(base, quote):
        return 1.0, prices_route.datetime.now()

    monkeypatch.setattr(prices_route, "refresh_asset_quote", fake_refresh)
    monkeypatch.setattr(prices_route, "get_fx_rate", fake_get_fx)

    # primeiro cria o asset
    client.post(
        "/api/assets",
        headers=headers,
        json={"symbol": "MOCK1", "name": "Mock asset"},
    )

    resp = client.post(
        "/api/prices/refresh",
        headers=headers,
        json={"symbols": ["MOCK1"], "force": True},
    )
    assert resp.status_code == 200
    assert called["count"] == 1
    data = resp.json()["quotes"]["MOCK1"]
    assert data["price"] == 10.0

from app.services.quotes import QuoteNotFoundError
from app.routes import prices as prices_route


def test_refresh_quotes_returns_404_on_quote_error(client, user_token, monkeypatch):
    headers, _ = user_token
    client.post(
        "/api/assets",
        headers=headers,
        json={"symbol": "ERR1", "name": "Err Asset"},
    )

    def fake_refresh(db, asset, force=False):
        raise QuoteNotFoundError(asset.symbol)

    monkeypatch.setattr(prices_route, "refresh_asset_quote", fake_refresh)

    resp = client.post(
        "/api/prices/refresh",
        headers=headers,
        json={"symbols": ["ERR1"], "force": True},
    )
    assert resp.status_code == 404

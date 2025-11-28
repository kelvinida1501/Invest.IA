from app.routes import assets as assets_route


def test_create_and_get_asset(client):
    # create new asset
    resp = client.post(
        "/api/assets",
        json={
            "symbol": "TEST3",
            "name": "Test Asset",
            "currency": "usd",
            "class": "acao",
        },
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["symbol"] == "TEST3"
    assert payload["currency"] == "USD"

    # list all
    listing = client.get("/api/assets")
    assert listing.status_code == 200
    assert any(item["symbol"] == "TEST3" for item in listing.json())

    # fetch by symbol param
    single = client.get("/api/assets", params={"symbol": "TEST3"})
    assert single.status_code == 200
    assert single.json()["name"] == "Test Asset"


def test_search_assets_uses_cache(client, monkeypatch):
    calls = {"count": 0}

    def fake_hit(query: str, limit: int):
        calls["count"] += 1
        return [{"symbol": "CACHE", "shortname": "Cache Result"}]

    monkeypatch.setattr(assets_route, "_hit_yahoo", fake_hit)
    monkeypatch.setattr(assets_route, "_SEARCH_CACHE", {})
    monkeypatch.setattr(assets_route, "_SEARCH_INFLIGHT", set())

    monkeypatch.setattr(assets_route, "_enforce_rate_limit", lambda ip: None)

    first = client.get("/api/assets/search", params={"q": "PETR4", "limit": 2})
    assert first.status_code == 200
    assert calls["count"] == 1

    second = client.get("/api/assets/search", params={"q": "PETR4", "limit": 2})
    assert second.status_code == 200
    # cache hit, no new call
    assert calls["count"] == 1

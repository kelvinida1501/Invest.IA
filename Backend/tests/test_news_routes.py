from app.routes import news as news_route


def test_news_with_no_symbols_returns_no_items(client, user_token, monkeypatch):
    headers, _ = user_token

    monkeypatch.setattr(news_route, "_load_user_symbols", lambda db, uid: [])
    resp = client.get("/api/news", headers=headers, params={"debug": True})

    assert resp.status_code == 200
    data = resp.json()
    assert data["symbols"] == []
    assert data["items"] == []
    assert data["meta"]["debug"]["reason"] == "no_symbols"


def test_news_with_explicit_symbols_calls_service(client, user_token, monkeypatch):
    headers, _ = user_token
    called = {"args": None}

    def fake_fetch(symbols, **kwargs):
        called["args"] = symbols
        return {"symbols": symbols, "items": [{"url": "u", "headline": "h"}], "meta": {}}

    monkeypatch.setattr(news_route, "fetch_news_for_symbols", fake_fetch)
    resp = client.get("/api/news/raw", headers=headers, params={"symbols": "ABCD,EFGH"})
    assert resp.status_code == 200
    assert called["args"] == ["ABCD", "EFGH"]

def _setup_simple_portfolio(client, headers):
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "ALLOC1", "quantity": 2, "avg_price": 10}],
    )


def test_portfolio_allocation_endpoint(client, user_token, monkeypatch):
    headers, _ = user_token
    _setup_simple_portfolio(client, headers)

    # evita chamadas de FX/histórico
    monkeypatch.setattr(
        "app.routes.portfolio.ensure_history_for_assets", lambda *args, **kwargs: None
    )
    monkeypatch.setattr("app.routes.portfolio.get_fx_rate", lambda a, b: (1.0, None))

    resp = client.get(
        "/api/portfolio/allocation", headers=headers, params={"mode": "asset"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] in ("asset", "class")
    assert body["total"] >= 0
    assert isinstance(body["items"], list)


def test_portfolio_timeseries_endpoint(client, user_token, monkeypatch):
    headers, _ = user_token
    _setup_simple_portfolio(client, headers)
    monkeypatch.setattr(
        "app.routes.portfolio.ensure_history_for_assets", lambda *args, **kwargs: None
    )
    monkeypatch.setattr("app.routes.portfolio.get_fx_rate", lambda a, b: (1.0, None))

    resp = client.get(
        "/api/portfolio/timeseries", headers=headers, params={"range": "1m"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "series" in body
    assert isinstance(body["series"], list)

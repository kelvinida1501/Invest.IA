def test_portfolio_summary_returns_totals(client, user_token):
    headers, _ = user_token
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "SUM1", "quantity": 2, "avg_price": 50}],
    )

    resp = client.get("/api/portfolio/summary", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["market_total"] > 0
    assert len(body.get("itens", [])) >= 1

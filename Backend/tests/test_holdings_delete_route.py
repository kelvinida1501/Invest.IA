def test_delete_holding(client, user_token):
    headers, _ = user_token
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "DEL1", "quantity": 1, "avg_price": 10}],
    )
    holdings = client.get("/api/portfolio/summary", headers=headers)
    assert holdings.status_code == 200
    items = holdings.json().get("itens") or holdings.json().get("items") or []
    hid = items[0]["holding_id"]

    resp = client.delete(f"/api/holdings/{hid}", headers=headers)
    assert resp.status_code == 204

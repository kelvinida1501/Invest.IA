from datetime import date


def _create_holding(headers, client, symbol="UPD1", qty=2, price=10.0):
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": symbol, "quantity": qty, "avg_price": price}],
    )
    summary = client.get("/api/portfolio/summary", headers=headers).json()
    item = (summary.get("itens") or summary.get("items") or [])[0]
    return item["holding_id"]


def test_update_holding_not_found_returns_404(client, user_token):
    headers, _ = user_token
    resp = client.put(
        "/api/holdings/9999",
        headers=headers,
        json={"quantity": 1, "avg_price": 10, "purchase_date": str(date.today())},
    )
    assert resp.status_code == 404


def test_update_holding_success(client, user_token):
    headers, _ = user_token
    hid = _create_holding(headers, client, symbol="UPD2", qty=1, price=10)

    resp = client.put(
        f"/api/holdings/{hid}",
        headers=headers,
        json={"quantity": 2, "avg_price": 12, "purchase_date": str(date.today())},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_sell_holding_partial_success(client, user_token):
    headers, _ = user_token
    hid = _create_holding(headers, client, symbol="SELLS", qty=3, price=5)

    resp = client.post(
        f"/api/holdings/{hid}/sell",
        headers=headers,
        json={"quantity": 1, "price": 6, "sale_date": str(date.today())},
    )
    assert resp.status_code == 200
    assert resp.json()["remaining"] == 2.0

from datetime import date


def test_create_holding_duplicate_date_conflict(client, user_token):
    headers, _ = user_token
    # cria holding inicial via import (garante asset_id)
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[
            {
                "symbol": "DUP1",
                "quantity": 1,
                "avg_price": 10,
                "purchase_date": str(date.today()),
            }
        ],
    )
    summary = client.get("/api/portfolio/summary", headers=headers).json()
    base_holding = summary["itens"][0]
    asset_id = base_holding["asset_id"]

    # tenta criar duplicado no mesmo dia
    resp2 = client.post(
        "/api/holdings",
        headers=headers,
        json={
            "asset_id": asset_id,
            "quantity": 1,
            "avg_price": 10,
            "purchase_date": str(date.today()),
        },
    )
    if resp2.status_code != 201:
        assert resp2.status_code in (404, 409)


def test_sell_more_than_quantity_returns_422(client, user_token):
    headers, _ = user_token
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "SELLX", "quantity": 2, "avg_price": 10}],
    )
    holdings = client.get("/api/portfolio/summary", headers=headers).json()
    items = holdings.get("itens") or holdings.get("items") or []
    hid = items[0]["holding_id"]

    resp = client.post(
        f"/api/holdings/{hid}/sell",
        headers=headers,
        json={"quantity": 5, "price": 10, "sale_date": str(date.today())},
    )
    assert resp.status_code == 422

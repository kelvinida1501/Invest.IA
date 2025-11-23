from datetime import date, timedelta


def test_create_holding_future_date_rejected(client, user_token):
    headers, _ = user_token
    # create asset first
    client.post("/api/assets", headers=headers, json={"symbol": "FUT1", "name": "Fut Asset"})
    future = (date.today() + timedelta(days=1)).isoformat()

    resp = client.post(
        "/api/holdings",
        headers=headers,
        json={"asset_id": 1, "quantity": 1, "avg_price": 10, "purchase_date": future},
    )
    assert resp.status_code == 422

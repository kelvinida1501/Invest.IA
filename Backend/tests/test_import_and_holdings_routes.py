from datetime import date

from app.db.models import Holding


def test_import_holdings_creates_and_updates(client, user_token, db_session):
    headers, _ = user_token
    # create two holdings
    resp = client.post(
        "/api/import/holdings",
        headers=headers,
        json=[
            {"symbol": "PETR4.SA", "quantity": 10, "avg_price": 20.0},
            {"symbol": "VALE3.SA", "quantity": 5, "avg_price": 60.0},
        ],
    )
    assert resp.status_code == 200
    assert resp.json()["created"] == 2

    # update one
    resp2 = client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "PETR4.SA", "quantity": 15, "avg_price": 22.0}],
    )
    assert resp2.status_code == 200
    assert resp2.json()["updated"] == 1

    rows = db_session.query(Holding).all()
    assert len(rows) == 2


def test_create_and_sell_holding(client, user_token, db_session):
    headers, _ = user_token
    # cria import para ter um holding
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "ITUB4.SA", "quantity": 4, "avg_price": 25.0}],
    )
    holding = db_session.query(Holding).first()
    assert holding is not None

    # vender parcialmente
    sale = client.post(
        f"/api/holdings/{holding.id}/sell",
        headers=headers,
        json={"quantity": 2, "price": 30.0, "sale_date": str(date.today())},
    )
    assert sale.status_code == 200
    assert sale.json()["remaining"] == 2.0

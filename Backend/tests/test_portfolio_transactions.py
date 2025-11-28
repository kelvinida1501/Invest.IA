from datetime import datetime, timezone

from app.db.models import Asset, Transaction
from app.services.portfolio_utils import get_or_create_default_portfolio


def test_portfolio_transactions_list(client, user_token, db_session):
    headers, _ = user_token
    portfolio = get_or_create_default_portfolio(db_session, _.id)
    asset = Asset(symbol="TRX1", name="Trx", class_="acao", currency="BRL")
    db_session.add(asset)
    db_session.commit()
    txn = Transaction(
        portfolio_id=portfolio.id,
        asset_id=asset.id,
        type="buy",
        quantity=1,
        price=10,
        total=10,
        executed_at=datetime.now(timezone.utc),
        status="active",
    )
    db_session.add(txn)
    db_session.commit()

    resp = client.get("/api/portfolio/transactions", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, dict)
    assert body.get("items") or []

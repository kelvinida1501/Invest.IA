from datetime import datetime, timezone

from app.db.models import Asset, Portfolio, Transaction, User
from app.services.portfolio_utils import record_transaction


def test_record_transaction_persists_with_normalized_timestamp(db_session):
    user = User(name="U", email="u@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    portfolio = Portfolio(user_id=user.id, name="Principal")
    asset = Asset(symbol="TEST", name="Test Asset", class_="acao", currency="USD")
    db_session.add_all([portfolio, asset])
    db_session.commit()

    executed = datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc)
    record_transaction(
        db_session,
        portfolio.id,
        asset.id,
        "buy",
        2.5,
        10.0,
        executed_at=executed,
        note="unit-test",
    )
    db_session.commit()

    rows = db_session.query(Transaction).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.total == 25.0
    # Executed_at deve estar em UTC "naive"
    assert row.executed_at.tzinfo is None
    assert row.note == "unit-test"

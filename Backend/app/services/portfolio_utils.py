from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.db.models import Portfolio, Transaction


def get_or_create_default_portfolio(db: Session, user_id: int) -> Portfolio:
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user_id)
        .order_by(Portfolio.id.asc())
        .first()
    )
    if portfolio:
        return portfolio

    portfolio = Portfolio(user_id=user_id, name="Principal")
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


def record_transaction(
    db: Session,
    portfolio_id: int,
    asset_id: int,
    tx_type: str,
    quantity: float,
    price: float,
    *,
    executed_at: datetime | None = None,
    kind: str = "trade",
    source: str = "auto",
    note: str | None = None,
    status: str = "active",
) -> None:
    qty = abs(float(quantity))
    if qty <= 0:
        return

    price = float(price)
    when = executed_at or datetime.now(timezone.utc)
    if when.tzinfo is not None:
        when = when.astimezone(timezone.utc).replace(tzinfo=None)
    db.add(
        Transaction(
            portfolio_id=portfolio_id,
            asset_id=asset_id,
            type=tx_type,
            quantity=qty,
            price=price,
            total=price * qty,
            executed_at=when,
            kind=kind,
            source=source,
            note=note,
            status=status,
        )
    )

from fastapi import APIRouter, Depends
from pydantic import BaseModel, condecimal, confloat
from sqlalchemy.orm import Session
from decimal import Decimal

from app.db.base import get_db
from app.db.models import Asset, Holding
from app.routes.holdings import get_or_create_default_portfolio  # reuso
from app.routes.auth import get_current_user, User  # type: ignore

router = APIRouter(prefix="/import", tags=["import"])


class HoldingInput(BaseModel):
    symbol: str
    quantity: confloat(gt=0)
    avg_price: condecimal(gt=Decimal("0"))


def get_or_create_asset(db: Session, symbol: str) -> Asset:
    s = symbol.strip().upper()
    a = db.query(Asset).filter(Asset.symbol == s).first()
    if a:
        return a
    a = Asset(symbol=s, name=s, class_="acao", currency="BRL")
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


@router.post("/holdings")
def import_holdings(
    items: list[HoldingInput],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = get_or_create_default_portfolio(db, user.id)
    created, updated = 0, 0

    for it in items:
        a = get_or_create_asset(db, it.symbol)
        h = (
            db.query(Holding)
            .filter(
                Holding.portfolio_id == portfolio.id,
                Holding.asset_id == a.id,
            )
            .first()
        )

        if h:
            h.quantity = float(it.quantity)
            h.avg_price = float(it.avg_price)
            updated += 1
        else:
            db.add(
                Holding(
                    portfolio_id=portfolio.id,
                    asset_id=a.id,
                    quantity=float(it.quantity),
                    avg_price=float(it.avg_price),
                )
            )
            created += 1

    db.commit()
    return {"created": created, "updated": updated}

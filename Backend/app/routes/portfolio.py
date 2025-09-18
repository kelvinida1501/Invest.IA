from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import get_db

from app.db.models import Portfolio, Holding, Asset

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# MVP: assumimos portfolio padrão id=1 para o user 1
DEFAULT_USER_ID = 1

def _get_or_create_default_portfolio(db: Session, user_id: int):
    p = db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
    if not p:
        p = Portfolio(user_id=user_id, name="Principal")
        db.add(p); db.commit(); db.refresh(p)
    return p

@router.get("")
def get_portfolio(db: Session = Depends(get_db)):
    portfolio = _get_or_create_default_portfolio(db, DEFAULT_USER_ID)
    holdings = (
        db.query(Holding, Asset)
        .join(Asset, Asset.id == Holding.asset_id)
        .filter(Holding.portfolio_id == portfolio.id)
        .all()
    )
    # Sem preço de mercado ainda: usar valor = quantity * avg_price (proxy)
    itens = []
    total = 0.0
    for h, a in holdings:
        valor = h.quantity * h.avg_price
        total += valor
        itens.append({
            "holding_id": h.id,
            "asset_id": a.id,
            "ticker": a.symbol,
            "name": a.name,
            "class": a.class_,
            "quantity": h.quantity,
            "avg_price": h.avg_price,
            "valor": valor,
        })
    # calcular %
    for i in itens:
        i["pct"] = (i["valor"] / total) * 100 if total > 0 else 0.0
    return {"portfolio_id": portfolio.id, "total": total, "itens": itens}

@router.post("/holdings")
def upsert_holding(ticker: str, quantity: float, avg_price: float, db: Session = Depends(get_db)):
    ticker = ticker.upper().strip()
    asset = db.query(Asset).filter(Asset.symbol == ticker).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset não encontrado. Cadastre em /assets primeiro.")

    portfolio = _get_or_create_default_portfolio(db, DEFAULT_USER_ID)

    holding = db.query(Holding).filter(
        Holding.portfolio_id == portfolio.id, Holding.asset_id == asset.id
    ).first()
    if holding:
        holding.quantity = quantity
        holding.avg_price = avg_price
    else:
        holding = Holding(portfolio_id=portfolio.id, asset_id=asset.id, quantity=quantity, avg_price=avg_price)
        db.add(holding)
    db.commit()
    db.refresh(holding)
    return {"ok": True, "holding_id": holding.id}

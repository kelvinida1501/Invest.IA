from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, condecimal, confloat

from app.db.base import get_db
from app.db.models import Holding, Asset, Portfolio
from app.routes.auth import get_current_user, User  # type: ignore

router = APIRouter(prefix="/holdings", tags=["holdings"])


class HoldingCreate(BaseModel):
    asset_id: int
    quantity: confloat(gt=0)
    avg_price: condecimal(gt=0)


class HoldingUpdate(BaseModel):
    quantity: confloat(gt=0)
    avg_price: condecimal(gt=0)


def row_to_json(h: Holding):
    a: Asset = h.asset
    last_price = float(h.avg_price)  # MVP: usa o preço médio como "último"
    valor = float(h.quantity) * last_price
    return {
        "holding_id": h.id,
        "asset_id": h.asset_id,
        "symbol": a.symbol,
        "name": a.name,
        "class": a.class_,
        "quantity": float(h.quantity),
        "avg_price": float(h.avg_price),
        "last_price": last_price,
        "valor": valor,
        "pct": 0.0,  # preenchido no /portfolio/summary
    }


def get_or_create_default_portfolio(db: Session, user_id: int) -> Portfolio:
    p = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user_id)
        .order_by(Portfolio.id.asc())
        .first()
    )
    if p:
        return p
    p = Portfolio(user_id=user_id, name="Principal")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.post("", status_code=201)
def create_holding(
    body: HoldingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # portfolio padrão do usuário
    portfolio = get_or_create_default_portfolio(db, user.id)

    a = db.query(Asset).get(body.asset_id)
    if not a:
        raise HTTPException(status_code=404, detail="Asset não encontrado")

    # UniqueConstraint(portfolio_id, asset_id): se já existir, atualiza
    h = (
        db.query(Holding)
        .filter(Holding.portfolio_id == portfolio.id, Holding.asset_id == body.asset_id)
        .first()
    )

    if h:
        h.quantity = float(body.quantity)
        h.avg_price = float(body.avg_price)
        h.updated_at = datetime.utcnow()
        db.commit()
        return {"id": h.id}

    h = Holding(
        portfolio_id=portfolio.id,
        asset_id=body.asset_id,
        quantity=float(body.quantity),
        avg_price=float(body.avg_price),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return {"id": h.id}


@router.put("/{holding_id}")
def update_holding(
    holding_id: int,
    body: HoldingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = get_or_create_default_portfolio(db, user.id)
    h = (
        db.query(Holding)
        .filter(Holding.id == holding_id, Holding.portfolio_id == portfolio.id)
        .first()
    )
    if not h:
        raise HTTPException(status_code=404, detail="Holding não encontrada")

    h.quantity = float(body.quantity)
    h.avg_price = float(body.avg_price)
    h.updated_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.delete("/{holding_id}", status_code=204)
def delete_holding(
    holding_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = get_or_create_default_portfolio(db, user.id)
    h = (
        db.query(Holding)
        .filter(Holding.id == holding_id, Holding.portfolio_id == portfolio.id)
        .first()
    )
    if not h:
        raise HTTPException(status_code=404, detail="Holding não encontrada")
    db.delete(h)
    db.commit()

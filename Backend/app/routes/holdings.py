from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, condecimal, confloat

from app.db.base import get_db
from app.db.models import Holding, Asset, Portfolio, Transaction
from app.routes.auth import get_current_user, User  # type: ignore
from app.services.quotes import QuoteNotFoundError, refresh_asset_quote

router = APIRouter(prefix="/holdings", tags=["holdings"])


class HoldingCreate(BaseModel):
    asset_id: int
    quantity: confloat(gt=0)
    avg_price: condecimal(gt=0)
    purchase_date: date | None = None


class HoldingUpdate(BaseModel):
    quantity: confloat(gt=0)
    avg_price: condecimal(gt=0)
    purchase_date: date | None = None


class HoldingSell(BaseModel):
    quantity: confloat(gt=0)
    price: condecimal(gt=0)
    sale_date: date


def row_to_json(h: Holding):
    a: Asset = h.asset
    last_price = float(h.avg_price)  # MVP: usa o preco medio como "ultimo"
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
        "created_at": h.created_at.isoformat() if h.created_at else None,
        "updated_at": h.updated_at.isoformat() if h.updated_at else None,
        "purchase_date": h.purchase_date.isoformat() if h.purchase_date else None,
    }


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
    executed_at: datetime | None = None,
    *,
    kind: str = "trade",
    source: str = "auto",
    note: str | None = None,
    status: str = "active",
) -> None:
    qty = abs(float(quantity))
    if qty <= 0:
        return
    price = float(price)
    when = executed_at or datetime.utcnow()
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


@router.post("", status_code=201)
def create_holding(
    body: HoldingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = get_or_create_default_portfolio(db, user.id)

    asset = db.query(Asset).get(body.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nao encontrado")

    try:
        refresh_asset_quote(db, asset, force=True)
    except QuoteNotFoundError:
        pass

    purchase_dt = body.purchase_date or date.today()
    if purchase_dt > date.today():
        raise HTTPException(
            status_code=422, detail="Data de compra nao pode ser futura"
        )
    purchase_dt_dt = datetime.combine(purchase_dt, datetime.min.time())

    # Verifica se já existe lote do mesmo ativo na mesma data
    same_day = (
        db.query(Holding)
        .filter(
            Holding.portfolio_id == portfolio.id,
            Holding.asset_id == body.asset_id,
            Holding.purchase_date == purchase_dt,
        )
        .first()
    )
    if same_day:
        # Bloqueia inclusão duplicada no mesmo dia – usuário deve editar o registro existente
        raise HTTPException(
            status_code=409,
            detail="Ja existe compra deste ativo nesta data. Edite o registro existente.",
        )

    holding = Holding(
        portfolio_id=portfolio.id,
        asset_id=body.asset_id,
        quantity=float(body.quantity),
        avg_price=float(body.avg_price),
        purchase_date=purchase_dt,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(holding)
    record_transaction(
        db,
        portfolio.id,
        body.asset_id,
        "buy",
        float(body.quantity),
        float(body.avg_price),
        executed_at=purchase_dt_dt,
    )
    db.commit()
    db.refresh(holding)
    return {"id": holding.id}


@router.put("/{holding_id}")
def update_holding(
    holding_id: int,
    body: HoldingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = get_or_create_default_portfolio(db, user.id)
    holding = (
        db.query(Holding)
        .filter(Holding.id == holding_id, Holding.portfolio_id == portfolio.id)
        .first()
    )
    if not holding:
        raise HTTPException(status_code=404, detail="Holding nao encontrada")

    try:
        refresh_asset_quote(db, holding.asset, force=True)
    except QuoteNotFoundError:
        pass

    before_qty = float(holding.quantity)
    before_avg = float(holding.avg_price)
    new_qty = float(body.quantity)
    new_avg = float(body.avg_price)

    holding.quantity = new_qty
    holding.avg_price = new_avg
    holding.updated_at = datetime.utcnow()
    if body.purchase_date:
        if body.purchase_date > date.today():
            raise HTTPException(
                status_code=422, detail="Data de compra nao pode ser futura"
            )
        # Evita colisão de unicidade ao alterar a data
        conflict = (
            db.query(Holding)
            .filter(
                Holding.portfolio_id == portfolio.id,
                Holding.asset_id == holding.asset_id,
                Holding.purchase_date == body.purchase_date,
                Holding.id != holding.id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Ja existe compra deste ativo nesta data. "
                    "Escolha outra data ou edite o registro correspondente."
                ),
            )
        holding.purchase_date = body.purchase_date

    delta_qty = new_qty - before_qty
    if abs(delta_qty) > 1e-9:
        base_date = body.purchase_date or holding.purchase_date or date.today()
        exec_dt = datetime.combine(base_date, datetime.min.time())
        record_transaction(
            db,
            portfolio.id,
            holding.asset_id,
            "buy" if delta_qty > 0 else "sell",
            delta_qty,
            new_avg if delta_qty > 0 else before_avg,
            executed_at=exec_dt,
        )
    db.commit()
    return {"ok": True}


@router.post("/{holding_id}/sell")
def sell_holding(
    holding_id: int,
    body: HoldingSell,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.sale_date > date.today():
        raise HTTPException(status_code=422, detail="Data de venda nao pode ser futura")

    qty = float(body.quantity)
    price = float(body.price)
    sale_dt = datetime.combine(body.sale_date, datetime.min.time())

    portfolio = get_or_create_default_portfolio(db, user.id)
    holding = (
        db.query(Holding)
        .filter(Holding.id == holding_id, Holding.portfolio_id == portfolio.id)
        .first()
    )
    if not holding:
        raise HTTPException(status_code=404, detail="Holding nao encontrada")

    if qty > float(holding.quantity):
        raise HTTPException(
            status_code=422,
            detail="Quantidade de venda maior que a posicao atual",
        )

    new_qty = float(holding.quantity) - qty
    record_transaction(
        db,
        portfolio.id,
        holding.asset_id,
        "sell",
        qty,
        price,
        executed_at=sale_dt,
    )

    if new_qty <= 0:
        db.delete(holding)
    else:
        holding.quantity = new_qty
        holding.updated_at = datetime.utcnow()
    db.commit()
    return {"remaining": max(new_qty, 0.0)}


@router.delete("/{holding_id}", status_code=204)
def delete_holding(
    holding_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = get_or_create_default_portfolio(db, user.id)
    holding = (
        db.query(Holding)
        .filter(Holding.id == holding_id, Holding.portfolio_id == portfolio.id)
        .first()
    )
    if not holding:
        raise HTTPException(status_code=404, detail="Holding nao encontrada")

    db.delete(holding)
    db.commit()

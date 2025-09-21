from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
from datetime import date as date_type
from pydantic import BaseModel, condecimal
import random

from app.db.base import get_db
from app.db.models import Asset, AssetPrice

router = APIRouter(prefix="/prices", tags=["prices"])


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


def upsert_price_row(
    db: Session, asset_id: int, d: date_type, close_val: float
) -> AssetPrice:
    p = (
        db.query(AssetPrice)
        .filter(and_(AssetPrice.asset_id == asset_id, AssetPrice.date == d))
        .first()
    )
    if p:
        p.close = close_val
    else:
        p = AssetPrice(asset_id=asset_id, date=d, close=close_val)
        db.add(p)
    return p


class PriceUpsert(BaseModel):
    symbol: str
    date: str  # "YYYY-MM-DD"
    close: condecimal(gt=0)


@router.post("/update-random")
def update_random_prices(db: Session = Depends(get_db)):
    assets = db.query(Asset).all()
    if not assets:
        return {"updated": 0, "message": "Nenhum ativo encontrado"}

    today = datetime.utcnow().date()
    updated = 0
    for a in assets:
        price = round(random.uniform(10, 100), 2)
        upsert_price_row(db, a.id, today, float(price))
        updated += 1

    db.commit()
    return {
        "updated": updated,
        "date": str(today),
        "message": "Preços simulados atualizados",
    }


@router.post("/upsert", status_code=201)
def upsert_price(body: PriceUpsert, db: Session = Depends(get_db)):
    a = get_or_create_asset(db, body.symbol)
    try:
        d: date_type = datetime.strptime(body.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="Data inválida. Use YYYY-MM-DD.")

    p = upsert_price_row(db, a.id, d, float(body.close))
    db.commit()
    return {
        "asset_id": a.id,
        "symbol": a.symbol,
        "date": str(d),
        "close": float(p.close),
    }


@router.post("/bulk-upsert", status_code=201)
def bulk_upsert(prices: list[PriceUpsert], db: Session = Depends(get_db)):
    out = []
    for item in prices:
        out.append(upsert_price(item, db))
    return out


@router.get("/latest/{symbol}")
def latest_price(symbol: str, db: Session = Depends(get_db)):
    s = symbol.strip().upper()
    a = db.query(Asset).filter(Asset.symbol == s).first()
    if not a:
        raise HTTPException(status_code=404, detail="Asset não encontrado")

    p = (
        db.query(AssetPrice)
        .filter(AssetPrice.asset_id == a.id)
        .order_by(AssetPrice.date.desc())
        .first()
    )
    if not p:
        return {"symbol": a.symbol, "date": None, "close": None}
    return {"symbol": a.symbol, "date": str(p.date), "close": float(p.close)}

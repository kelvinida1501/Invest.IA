from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field

from app.db.base import get_db
from app.db.models import Asset

router = APIRouter(prefix="/assets", tags=["assets"])


class AssetCreate(BaseModel):
    symbol: str
    name: str | None = None
    class_: str | None = Field(default=None, alias="class")
    currency: str = "BRL"

    class Config:
        populate_by_name = True


def asset_to_json(a: Asset):
    return {
        "id": a.id,
        "symbol": a.symbol,
        "name": a.name,
        "class": a.class_,
        "currency": a.currency,
    }


@router.get("")
def get_assets(symbol: str | None = Query(default=None), db: Session = Depends(get_db)):
    if symbol:
        a = (
            db.query(Asset)
            .filter(func.upper(Asset.symbol) == symbol.strip().upper())
            .first()
        )
        if not a:
            raise HTTPException(status_code=404, detail="Asset não encontrado")
        return asset_to_json(a)

    return [
        asset_to_json(a) for a in db.query(Asset).order_by(Asset.symbol.asc()).all()
    ]


@router.post("", status_code=201)
def create_asset(body: AssetCreate, db: Session = Depends(get_db)):
    symbol = body.symbol.strip().upper()
    exists = db.query(Asset).filter(Asset.symbol == symbol).first()
    if exists:
        return asset_to_json(exists)

    a = Asset(
        symbol=symbol,
        name=(body.name or symbol),
        class_=(body.class_ or "acao"),
        currency=(body.currency or "BRL"),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return asset_to_json(a)

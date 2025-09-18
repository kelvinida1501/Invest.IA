from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import get_db

from app.db.models import Asset

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("")
def list_assets(db: Session = Depends(get_db)):
    return db.query(Asset).order_by(Asset.symbol.asc()).all()


@router.post("")
def create_asset(
    symbol: str,
    name: str | None = None,
    class_: str | None = None,
    currency: str = "BRL",
    db: Session = Depends(get_db),
):
    symbol = symbol.upper().strip()
    exists = db.query(Asset).filter(Asset.symbol == symbol).first()
    if exists:
        raise HTTPException(status_code=409, detail="Asset já cadastrado")
    asset = Asset(symbol=symbol, name=name, class_=class_, currency=currency)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset

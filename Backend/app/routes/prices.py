from __future__ import annotations

from datetime import datetime
from datetime import date as date_type
from typing import Iterable, Dict, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, condecimal, validator
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Asset, AssetPrice
from app.routes.auth import get_current_user, User  # type: ignore
from app.services.fx import FxRateNotFoundError, get_fx_rate
from app.services.quotes import QuoteNotFoundError, refresh_asset_quote
from app.services.currency import normalize_currency_code

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

    @validator("symbol")
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()


@router.post("/upsert", status_code=201)
def upsert_price(body: PriceUpsert, db: Session = Depends(get_db)):
    try:
        d: date_type = datetime.strptime(body.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="Data invalida. Use YYYY-MM-DD.")

    asset = get_or_create_asset(db, body.symbol)
    price = upsert_price_row(db, asset.id, d, float(body.close))
    db.commit()
    return {
        "asset_id": asset.id,
        "symbol": asset.symbol,
        "date": str(d),
        "close": float(price.close),
    }


class QuoteRefreshRequest(BaseModel):
    symbols: list[str]
    force: bool = False

    @validator("symbols", pre=True, each_item=True)
    def _normalize(cls, value: str) -> str:
        return value.strip().upper()


def _load_assets_by_symbol(db: Session, symbols: Iterable[str]) -> dict[str, Asset]:
    records = (
        db.query(Asset).filter(Asset.symbol.in_([s.upper() for s in symbols])).all()
    )
    return {asset.symbol.upper(): asset for asset in records}


def _serialize_quote(
    asset: Asset,
    fx_cache: Dict[str, Tuple[float, datetime]] | None = None,
) -> dict:
    fx_cache = fx_cache or {}
    price_original = (
        float(asset.last_quote_price) if asset.last_quote_price is not None else None
    )
    currency = normalize_currency_code(asset.currency, asset.symbol)

    converted_price = price_original
    retrieved_at = asset.last_quote_at.isoformat() if asset.last_quote_at else None

    if price_original is not None and currency != "BRL":
        cache_key = f"{currency}:BRL"
        if cache_key in fx_cache:
            rate, fx_ts = fx_cache[cache_key]
        else:
            try:
                rate, fx_ts = get_fx_rate(currency, "BRL")
            except FxRateNotFoundError:  # pragma: no cover
                rate, fx_ts = 1.0, None
            fx_cache[cache_key] = (rate, fx_ts)
        converted_price = price_original * rate
        if fx_ts and not retrieved_at:
            retrieved_at = fx_ts.isoformat()

    return {
        "price": converted_price,
        "price_original": price_original,
        "currency": currency,
        "retrieved_at": retrieved_at,
    }


@router.post("/refresh")
def refresh_quotes(
    body: QuoteRefreshRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not body.symbols:
        return {"quotes": {}}

    symbol_map = _load_assets_by_symbol(db, body.symbols)
    missing = [s for s in body.symbols if s.upper() not in symbol_map]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Ativos nao encontrados: {', '.join(missing)}",
        )

    refreshed_any = False
    for asset in symbol_map.values():
        try:
            refreshed = refresh_asset_quote(db, asset, force=body.force)
        except QuoteNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Cotacao nao encontrada para {asset.symbol}",
            ) from exc
        refreshed_any = refreshed_any or refreshed

    fx_cache: Dict[str, Tuple[float, datetime]] = {}

    if refreshed_any:
        db.commit()
    else:
        db.flush()

    quotes = {
        symbol: _serialize_quote(asset, fx_cache) for symbol, asset in symbol_map.items()
    }
    return {"quotes": quotes}


@router.post("/refresh-all")
def refresh_all_quotes(
    body: QuoteRefreshRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not body.symbols:
        return {"quotes": {}}

    assets: dict[str, Asset] = {}
    for symbol in body.symbols:
        assets[symbol.upper()] = get_or_create_asset(db, symbol)

    refreshed_any = False
    for asset in assets.values():
        try:
            refreshed = refresh_asset_quote(db, asset, force=body.force)
        except QuoteNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail=f"Cotacao nao encontrada para {asset.symbol}",
            ) from exc
        refreshed_any = refreshed_any or refreshed

    fx_cache: Dict[str, Tuple[float, datetime]] = {}

    if refreshed_any:
        db.commit()

    return {
        "quotes": {
            symbol: _serialize_quote(asset, fx_cache) for symbol, asset in assets.items()
        }
    }


@router.get("/latest/{symbol}")
def latest_price(symbol: str, db: Session = Depends(get_db)):
    s = symbol.strip().upper()
    asset = db.query(Asset).filter(Asset.symbol == s).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nao encontrado")

    return {"symbol": asset.symbol, **_serialize_quote(asset)}


@router.get("/fx")
def fx_rate(
    base: str = Query(default="USD", min_length=3, max_length=3),
    quote: str = Query(default="BRL", min_length=3, max_length=3),
):
    base = base.upper()
    quote = quote.upper()
    try:
        rate, ts = get_fx_rate(base, quote)
    except FxRateNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"FX rate {base}/{quote} nao encontrado",
        ) from exc
    return {
        "pair": f"{base}/{quote}",
        "rate": rate,
        "retrieved_at": ts.isoformat(),
    }


@router.get("/history/{symbol}")
def price_history(symbol: str, db: Session = Depends(get_db)):
    s = symbol.strip().upper()
    asset = db.query(Asset).filter(Asset.symbol == s).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset nao encontrado")

    rows = (
        db.query(AssetPrice)
        .filter(AssetPrice.asset_id == asset.id)
        .order_by(AssetPrice.date.desc())
        .limit(60)
        .all()
    )
    return [
        {
            "date": str(row.date),
            "close": float(row.close),
            "source": "yfinance",
            "price_type": "close",
        }
        for row in rows
    ]

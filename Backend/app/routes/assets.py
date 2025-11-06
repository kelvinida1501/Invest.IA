import logging
import time
from typing import Dict, List, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from urllib.parse import quote_plus

from app.db.base import get_db
from app.db.models import Asset

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])

_SEARCH_CACHE: Dict[str, Tuple[float, List[dict]]] = {}
_SEARCH_INFLIGHT: set[str] = set()
_SEARCH_TTL = 300.0  # seconds
_RATE_LIMIT: Dict[str, Tuple[float, int]] = {}
_RATE_WINDOW = 1.0  # seconds
_RATE_MAX_PER_WINDOW = 1


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


def _cache_key(query: str, limit: int) -> str:
    return f"{query.strip().lower()}::{limit}"


def _from_cache(query: str, limit: int) -> List[dict] | None:
    key = _cache_key(query, limit)
    cached = _SEARCH_CACHE.get(key)
    if not cached:
        return None
    stamp, data = cached
    if time.time() - stamp > _SEARCH_TTL:
        _SEARCH_CACHE.pop(key, None)
        return None
    return data


def _store_cache(query: str, limit: int, data: List[dict]) -> None:
    _SEARCH_CACHE[_cache_key(query, limit)] = (time.time(), data)


def _enforce_rate_limit(ip: str) -> None:
    now = time.time()
    stamp, count = _RATE_LIMIT.get(ip, (0.0, 0))
    if now - stamp > _RATE_WINDOW:
        _RATE_LIMIT[ip] = (now, 1)
        return
    if count >= _RATE_MAX_PER_WINDOW:
        raise HTTPException(
            status_code=429,
            detail="Muitas buscas em sequência. Aguarde um segundo e tente novamente.",
        )
    _RATE_LIMIT[ip] = (stamp, count + 1)


def _hit_yahoo(query: str, limit: int) -> List[dict]:
    url = (
        "https://query1.finance.yahoo.com/v1/finance/search"
        f"?q={quote_plus(query.strip())}&quotesCount={limit}&newsCount=0&lang=pt-BR&region=BR"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    for attempt in range(2):
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                payload = resp.json()
                quotes = payload.get("quotes") or []
                results = [
                    {
                        "symbol": item.get("symbol"),
                        "shortname": item.get("shortname") or item.get("name"),
                        "longname": item.get("longname"),
                        "exchange": item.get("exchDisp") or item.get("exchange"),
                        "type": item.get("typeDisp") or item.get("quoteType"),
                    }
                    for item in quotes[:limit]
                ]
                logger.debug("Yahoo search success query=%s limit=%s results=%s", query, limit, len(results))
                return results
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            logger.warning(
                "Yahoo search failed status=%s query=%s attempt=%s", status, query, attempt
            )
            if status == 429 and attempt == 0:
                time.sleep(1.5)
                continue
            if status == 429:
                raise HTTPException(
                    status_code=429,
                    detail="Limite de consultas do Yahoo Finance atingido. Aguarde alguns segundos e tente novamente.",
                ) from exc
            raise HTTPException(
                status_code=status,
                detail="Falha ao consultar Yahoo Finance",
            ) from exc
        except Exception as exc:  # pragma: no cover
            logger.exception("Erro inesperado ao consultar Yahoo: query=%s", query)
            raise HTTPException(status_code=502, detail="Nao foi possivel obter dados do Yahoo") from exc

    return []


@router.get("")
def get_assets(symbol: str | None = Query(default=None), db: Session = Depends(get_db)):
    if symbol:
        a = (
            db.query(Asset)
            .filter(func.upper(Asset.symbol) == symbol.strip().upper())
            .first()
        )
        if not a:
            raise HTTPException(status_code=404, detail="Asset nao encontrado")
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


@router.get("/search")
def search_assets(
    request: Request,
    q: str = Query(min_length=1, description="Termo para busca no Yahoo Finance"),
    limit: int = Query(default=8, ge=1, le=20),
):
    client_ip = request.client.host if request.client else "unknown"
    _enforce_rate_limit(client_ip)

    cached = _from_cache(q, limit)
    if cached is not None:
        logger.debug("Yahoo search cache hit ip=%s query=%s", client_ip, q)
        return cached

    key = _cache_key(q, limit)
    while key in _SEARCH_INFLIGHT:
        logger.debug("Yahoo search inflight wait ip=%s query=%s", client_ip, q)
        time.sleep(0.05)
        cached = _from_cache(q, limit)
        if cached is not None:
            return cached

    _SEARCH_INFLIGHT.add(key)
    try:
        logger.info("Yahoo search request ip=%s query=%s limit=%s", client_ip, q, limit)
        results = _hit_yahoo(q, limit)
        _store_cache(q, limit, results)
        return results
    finally:
        _SEARCH_INFLIGHT.discard(key)

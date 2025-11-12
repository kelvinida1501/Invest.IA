from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import Asset, Holding, Portfolio
from app.routes.auth import User, get_current_user
from app.services.news import fetch_news_for_symbols

router = APIRouter(prefix="/news", tags=["news"])

DEFAULT_TOTAL_LIMIT = 12
DEFAULT_PER_SYMBOL = 3
DEFAULT_LOOKBACK_DAYS = 7
DEFAULT_ORDER = "recent"
ALLOWED_ORDERS = {"recent", "relevance"}


def _load_user_symbols(db: Session, user_id: int) -> List[str]:
    rows = (
        db.query(Asset.symbol)
        .join(Holding, Holding.asset_id == Asset.id)
        .join(Portfolio, Portfolio.id == Holding.portfolio_id)
        .filter(Portfolio.user_id == user_id)
        .distinct()
        .all()
    )
    return [symbol for (symbol,) in rows if symbol]


def _parse_symbols_param(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    return [token.strip().upper() for token in raw.split(",") if token.strip()]


def _build_payload(
    symbols: List[str],
    *,
    total_limit: int,
    per_symbol_limit: int,
    lookback_days: int,
    order: str,
    include_debug: bool,
):
    clamped_lookback = max(1, min(lookback_days, DEFAULT_LOOKBACK_DAYS))
    if not symbols:
        return {
            "symbols": [],
            "items": [],
            "meta": {
                "fetched": 0,
                "limit": total_limit,
                "per_symbol_limit": per_symbol_limit,
                "lookback_hours": clamped_lookback * 24,
                "order": order,
                "debug": {"reason": "no_symbols"} if include_debug else None,
            },
        }

    lookback = timedelta(days=clamped_lookback)
    order_key = (
        "recent"
        if order not in ALLOWED_ORDERS
        else ("recent" if order == "recent" else "score")
    )
    return fetch_news_for_symbols(
        symbols,
        lookback=lookback,
        total_limit=total_limit,
        per_symbol_limit=per_symbol_limit,
        order_by=order_key,
        include_debug=include_debug,
    )


@router.get("")
def list_news(
    total_limit: int = Query(
        DEFAULT_TOTAL_LIMIT, ge=1, le=50, description="Total de notícias agregadas."
    ),
    per_symbol_limit: int = Query(
        DEFAULT_PER_SYMBOL, ge=1, le=10, description="Máximo de notícias por ativo."
    ),
    lookback_days: int = Query(
        DEFAULT_LOOKBACK_DAYS,
        ge=1,
        le=DEFAULT_LOOKBACK_DAYS,
        description="Janela de busca em dias (máx. 7).",
    ),
    order: str = Query(DEFAULT_ORDER, description="Ordenação: recent | relevance."),
    symbols: Optional[str] = Query(
        None, description="Lista de tickers separados por vírgula para debug."
    ),
    debug: bool = Query(
        False, description="Retorna metadados extras para diagnóstico."
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    explicit = _parse_symbols_param(symbols)
    if not explicit:
        explicit = _load_user_symbols(db, current_user.id)
    return _build_payload(
        explicit,
        total_limit=total_limit,
        per_symbol_limit=per_symbol_limit,
        lookback_days=lookback_days,
        order=order,
        include_debug=debug,
    )


@router.get("/portfolio")
def list_news_for_portfolio(
    total_limit: int = Query(DEFAULT_TOTAL_LIMIT, ge=1, le=50),
    per_symbol_limit: int = Query(DEFAULT_PER_SYMBOL, ge=1, le=10),
    lookback_days: int = Query(DEFAULT_LOOKBACK_DAYS, ge=1, le=DEFAULT_LOOKBACK_DAYS),
    order: str = Query(DEFAULT_ORDER),
    debug: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    symbols = _load_user_symbols(db, current_user.id)
    return _build_payload(
        symbols,
        total_limit=total_limit,
        per_symbol_limit=per_symbol_limit,
        lookback_days=lookback_days,
        order=order,
        include_debug=debug,
    )


@router.get("/raw")
def list_news_raw(
    symbols: str = Query(..., description="Lista de tickers separados por vírgula."),
    total_limit: int = Query(DEFAULT_TOTAL_LIMIT, ge=1, le=50),
    per_symbol_limit: int = Query(DEFAULT_PER_SYMBOL, ge=1, le=10),
    lookback_days: int = Query(DEFAULT_LOOKBACK_DAYS, ge=1, le=DEFAULT_LOOKBACK_DAYS),
    order: str = Query(DEFAULT_ORDER),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    explicit = _parse_symbols_param(symbols)
    return _build_payload(
        explicit,
        total_limit=total_limit,
        per_symbol_limit=per_symbol_limit,
        lookback_days=lookback_days,
        order=order,
        include_debug=True,
    )

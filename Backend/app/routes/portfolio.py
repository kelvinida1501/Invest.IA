import json
from datetime import datetime, date, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple, Literal

from app.db.base import get_db
from app.db.models import (
    Holding,
    Portfolio,
    Asset,
    AssetPrice,
    RiskProfile,  # <- necessario no rebalance
    Transaction,
)
from app.routes.auth import get_current_user, User  # type: ignore
from app.services.fx import FxRateNotFoundError, get_fx_rate
from app.services.history import ensure_history_for_assets
from app.services.currency import normalize_currency_code
from app.services.allocations import (
    CLASS_LABELS,
    AllocationProfile,
    get_allocation_profile,
    normalize_asset_class,
)
from app.services.rebalance import (
    HoldingSnapshot,
    RebalanceOptions,
    rebalance_portfolio,
)
from app.services.portfolio_utils import record_transaction
from pydantic import BaseModel, field_validator, confloat, constr

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def _resolve_profile_context(
    db: Session, user_id: int, profile_override: Optional[str]
) -> tuple[Optional[RiskProfile], AllocationProfile, str, List[str]]:
    rp = db.query(RiskProfile).filter(RiskProfile.user_id == user_id).first()
    profile_source = "default"
    if profile_override:
        profile_key = profile_override.lower()
        profile_source = "override"
    elif rp:
        profile_key = (rp.profile or "moderado").lower()
        profile_source = "stored"
    else:
        profile_key = "moderado"

    allocation = get_allocation_profile(profile_key)

    rules_applied: List[str] = []
    if rp and rp.rules:
        try:
            loaded_rules = json.loads(rp.rules)
            if isinstance(loaded_rules, list):
                rules_applied = [str(item) for item in loaded_rules]
        except json.JSONDecodeError:
            rules_applied = []

    return rp, allocation, profile_source, rules_applied


def convert_to_brl(
    price: float,
    currency: Optional[str],
    fx_cache: Dict[str, tuple[float, Optional[datetime]]],
) -> tuple[float, float, Optional[datetime], str]:
    curr = normalize_currency_code(currency)
    if curr == "BRL":
        return price, 1.0, None, curr

    cached = fx_cache.get(curr)
    if cached:
        rate, ts = cached
    else:
        try:
            rate, ts = get_fx_rate(curr, "BRL")
        except FxRateNotFoundError:
            rate, ts = 1.0, None
        fx_cache[curr] = (rate, ts)
    return price * rate, rate, ts, curr


CLASS_NORMALIZATION = {
    "acao": "acao",
    "stock": "acao",
    "actions": "acao",
    "equity": "acao",
    "etf": "etf",
    "fundo": "fii",
    "fii": "fii",
    "reit": "fii",
    "cripto": "cripto",
    "crypto": "cripto",
    "moeda": "caixa",
    "cash": "caixa",
    "renda_fixa": "renda_fixa",
    "bonds": "renda_fixa",
}

CLASS_CANDIDATES: Dict[str, List[dict]] = {
    "acao": [
        {"symbol": "BOVA11", "description": "ETF que replica o Ibovespa"},
        {"symbol": "SMAL11", "description": "ETF focado em small caps"},
    ],
    "etf": [
        {"symbol": "IVVB11", "description": "Exposicao ao S&P 500 em BRL"},
        {"symbol": "ACWI", "description": "ETF global de renda variavel"},
    ],
    "fii": [
        {"symbol": "HGLG11", "description": "Fundo logistico de alta liquidez"},
        {"symbol": "KNRI11", "description": "Fundo multi-estrategia classico"},
    ],
    "cripto": [
        {"symbol": "HASH11", "description": "ETF com cesta de criptoativos"},
        {"symbol": "BTC", "description": "Exposicao direta a Bitcoin"},
    ],
}


def normalize_class(raw: Optional[str]) -> str:
    value = (raw or "acao").strip().lower()
    return CLASS_NORMALIZATION.get(value, "outros")


def _compose_dt(date_obj: Optional[datetime]) -> Optional[str]:
    if not date_obj:
        return None
    return date_obj.isoformat()


def _pick_price_rows(
    db: Session,
    asset: Asset,
) -> Tuple[Optional[float], Optional[datetime], Optional[float], Optional[datetime]]:
    current_price = (
        float(asset.last_quote_price) if asset.last_quote_price is not None else None
    )
    current_at = asset.last_quote_at

    # Busca últimos fechamentos registrados para fallback e referência anterior
    price_rows: List[AssetPrice] = (
        db.query(AssetPrice)
        .filter(AssetPrice.asset_id == asset.id)
        .order_by(AssetPrice.date.desc())
        .limit(2)
        .all()
    )

    prev_price = None
    prev_at = None
    if price_rows:
        latest_row = price_rows[0]
        latest_dt = datetime.combine(latest_row.date, datetime.min.time())
        if current_price is None:
            current_price = float(latest_row.close)
            current_at = latest_dt
        if len(price_rows) > 1:
            prev_row = price_rows[1]
            prev_price = float(prev_row.close)
            prev_at = datetime.combine(prev_row.date, datetime.min.time())

    return current_price, current_at, prev_price, prev_at


def _build_portfolio_snapshot(
    db: Session,
    portfolio: Portfolio,
) -> Tuple[
    List[dict],
    float,
    float,
    float,
    Dict[str, dict],
    Optional[datetime],
]:
    rows = (
        db.query(Holding)
        .options(joinedload(Holding.asset))
        .filter(Holding.portfolio_id == portfolio.id)
        .all()
    )

    itens: List[dict] = []
    invested_total = 0.0
    market_total = 0.0
    previous_total = 0.0
    fx_cache: Dict[str, tuple[float, Optional[datetime]]] = {}
    fx_meta: Dict[str, dict] = {}
    as_of: Optional[datetime] = None

    for holding in rows:
        asset = holding.asset
        normalized_class = normalize_class(asset.class_)
        quantity = float(holding.quantity)
        avg_price = float(holding.avg_price)
        invested_value = quantity * avg_price
        invested_total += invested_value

        price_now, price_at, prev_price_raw, prev_at = _pick_price_rows(db, asset)
        if price_now is None:
            price_now = avg_price
            price_at = holding.updated_at or holding.created_at

        converted_price, fx_rate, fx_ts, currency = convert_to_brl(
            float(price_now), asset.currency, fx_cache
        )
        current_value = quantity * converted_price
        market_total += current_value

        if price_at and (as_of is None or price_at > as_of):
            as_of = price_at

        if currency != "BRL" and currency not in fx_meta:
            fx_meta[currency] = {
                "pair": f"{currency}/BRL",
                "rate": fx_rate,
                "retrieved_at": fx_ts.isoformat() if fx_ts else None,
            }

        if prev_price_raw is None:
            prev_price_raw = price_now
            prev_at = price_at

        prev_converted, _, _, _ = convert_to_brl(
            float(prev_price_raw), asset.currency, fx_cache
        )
        previous_value = quantity * prev_converted
        previous_total += previous_value

        pnl_abs_item = current_value - invested_value
        pnl_pct_item = (
            (pnl_abs_item / invested_value * 100.0) if invested_value > 0 else 0.0
        )
        day_change_abs = current_value - previous_value
        day_change_pct = (
            (day_change_abs / previous_value * 100.0) if previous_value > 0 else 0.0
        )

        itens.append(
            {
                "holding_id": holding.id,
                "asset_id": holding.asset_id,
                "symbol": asset.symbol,
                "name": asset.name,
                "class": normalized_class,
                "class_original": asset.class_,
                "quantity": quantity,
                "avg_price": avg_price,
                "currency": currency,
                "last_price": converted_price,
                "last_price_original": float(price_now),
                "fx_rate": fx_rate if currency != "BRL" else None,
                "last_price_at": _compose_dt(price_at),
                "prev_price": prev_converted,
                "prev_price_original": float(prev_price_raw),
                "prev_price_at": _compose_dt(prev_at),
                "valor": current_value,
                "valor_prev": previous_value,
                "pct": 0.0,
                "pnl_abs": pnl_abs_item,
                "pnl_pct": pnl_pct_item,
                "day_change_abs": day_change_abs,
                "day_change_pct": day_change_pct,
                "created_at": (
                    holding.created_at.isoformat() if holding.created_at else None
                ),
                "updated_at": (
                    holding.updated_at.isoformat() if holding.updated_at else None
                ),
                "purchase_date": (
                    holding.purchase_date.isoformat() if holding.purchase_date else None
                ),
            }
        )

    total = market_total
    if total > 0:
        for item in itens:
            item["pct"] = round((item["valor"] / total) * 100.0, 2)

    return itens, invested_total, market_total, previous_total, fx_meta, as_of


def serialize_transaction(tx: Transaction) -> dict:
    asset = tx.asset
    executed_at = tx.executed_at
    if executed_at and executed_at.tzinfo is None:
        executed_at = executed_at.replace(tzinfo=timezone.utc)
    return {
        "id": tx.id,
        "symbol": asset.symbol if asset else "",
        "name": asset.name if asset else "",
        "type": tx.type,
        "quantity": float(tx.quantity),
        "price": float(tx.price),
        "total": float(tx.total),
        "executed_at": executed_at.isoformat() if executed_at else None,
        "status": tx.status,
        "kind": tx.kind,
        "source": tx.source,
        "note": tx.note,
        "reversal_of_id": tx.reversal_of_id,
    }


class TransactionUpdateRequest(BaseModel):
    quantity: Optional[float] = None
    price: Optional[float] = None
    executed_at: Optional[datetime] = None
    type: Optional[str] = None
    kind: Optional[str] = None
    note: Optional[str] = None

    @field_validator("quantity")
    def validate_quantity(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value <= 0:
            raise ValueError("quantity must be greater than zero")
        return value

    @field_validator("price")
    def validate_price(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("price must be zero or positive")
        return value

    @field_validator("type")
    def validate_type(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        norm = value.lower()
        if norm not in {"buy", "sell"}:
            raise ValueError("type must be 'buy' or 'sell'")
        return norm

    @field_validator("kind")
    def validate_kind(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        norm = value.lower()
        if norm not in {"trade", "adjust"}:
            raise ValueError("kind must be 'trade' or 'adjust'")
        return norm


class TransactionVoidRequest(BaseModel):
    note: Optional[str] = None


class RebalanceApplySuggestion(BaseModel):
    symbol: constr(strip_whitespace=True, min_length=1)
    action: Literal["comprar", "vender"]
    quantity: confloat(gt=0)
    price: confloat(gt=0)


class RebalanceApplyOptions(BaseModel):
    profile_override: Optional[str] = None
    allow_sells: bool = True
    prefer_etfs: bool = False
    min_trade_value: confloat(ge=0) = 100.0
    max_turnover: confloat(ge=0, le=1) = 0.25


class RebalanceApplyRequest(BaseModel):
    request_id: constr(strip_whitespace=True, min_length=6)
    suggestions: List[RebalanceApplySuggestion]
    options: RebalanceApplyOptions
    execution_date: Optional[date] = None


SERIES_RANGE_CHOICES = {"1M", "3M", "6M", "1A", "5A", "YTD", "ALL"}
SERIES_RANGE_DELTAS = {
    "1M": timedelta(days=30),
    "3M": timedelta(days=90),
    "6M": timedelta(days=180),
    "1A": timedelta(days=365),
    "5A": timedelta(days=365 * 5),
}


def _resolve_range_start(
    range_key: str,
    earliest_date: Optional[date],
    today: date,
) -> date:
    if earliest_date is None:
        earliest_date = today

    if earliest_date > today:
        earliest_date = today

    key = range_key.upper()
    if key == "ALL":
        return earliest_date
    if key == "YTD":
        year_start = date(today.year, 1, 1)
        return max(earliest_date, year_start)

    delta = SERIES_RANGE_DELTAS.get(key, SERIES_RANGE_DELTAS["6M"])
    candidate = today - delta
    return max(earliest_date, candidate)


def _derive_portfolio_earliest_date(
    portfolio: Portfolio,
    holdings: Iterable[Holding],
    transactions: Iterable[Transaction],
) -> Optional[date]:
    candidates: List[date] = []
    for h in holdings:
        if h.purchase_date:
            candidates.append(h.purchase_date)
        elif h.created_at:
            candidates.append(h.created_at.date())

    for tx in transactions:
        if tx.executed_at:
            candidates.append(tx.executed_at.date())

    if portfolio.created_at:
        candidates.append(portfolio.created_at.date())

    return min(candidates) if candidates else None


class RealizedPnlTracker:
    def __init__(self) -> None:
        self.qty_state: Dict[int, float] = defaultdict(float)
        self.avg_cost_state: Dict[int, float] = defaultdict(float)
        self.realized_total = 0.0
        self.realized_cost_basis = 0.0

    def apply(self, tx: Transaction, *, count_realized: bool = True) -> None:
        asset_id = tx.asset_id
        if asset_id is None:
            return

        tx_type = (tx.type or "").lower()
        if tx_type not in {"buy", "sell"}:
            return

        quantity = float(tx.quantity)
        if quantity <= 0:
            return

        price = float(tx.price) if tx.price is not None else None
        if price is None:
            total = float(tx.total) if tx.total is not None else 0.0
            price = total / quantity if quantity else 0.0
        current_qty = self.qty_state.get(asset_id, 0.0)
        avg_cost = self.avg_cost_state.get(asset_id, 0.0)

        if tx_type == "buy":
            total_cost = (avg_cost * current_qty) + (price * quantity)
            new_qty = current_qty + quantity
            self.qty_state[asset_id] = new_qty
            self.avg_cost_state[asset_id] = total_cost / new_qty if new_qty > 0 else 0.0
            return

        sell_qty = min(quantity, current_qty) if current_qty > 0 else quantity
        if sell_qty <= 0:
            return

        if count_realized:
            pnl = (price - avg_cost) * sell_qty
            self.realized_total += pnl
            self.realized_cost_basis += avg_cost * sell_qty

        new_qty = max(current_qty - sell_qty, 0.0)
        self.qty_state[asset_id] = new_qty
        if new_qty <= 0:
            self.avg_cost_state[asset_id] = 0.0


def _generate_portfolio_timeseries(
    db: Session,
    portfolio: Portfolio,
    holdings: List[Holding],
    range_key: str,
) -> dict:
    today = date.today()
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.portfolio_id == portfolio.id,
            Transaction.status == "active",
        )
        .order_by(Transaction.executed_at.asc(), Transaction.id.asc())
        .all()
    )

    earliest = _derive_portfolio_earliest_date(portfolio, holdings, transactions)
    start_date = _resolve_range_start(range_key, earliest, today)

    asset_ids = {tx.asset_id for tx in transactions if tx.asset_id is not None} | {
        h.asset_id for h in holdings
    }
    if not asset_ids:
        return {
            "as_of": today.isoformat(),
            "base_currency": "BRL",
            "earliest_date": earliest.isoformat() if earliest else None,
            "range": range_key,
            "start_date": start_date.isoformat(),
            "series": [],
        }

    asset_map: Dict[int, Asset] = {}
    for h in holdings:
        if h.asset:
            asset_map[h.asset_id] = h.asset

    missing_ids = asset_ids - set(asset_map.keys())
    if missing_ids:
        extra_assets = db.query(Asset).filter(Asset.id.in_(list(missing_ids))).all()
        for asset in extra_assets:
            asset_map[asset.id] = asset

    assets = [asset_map[asset_id] for asset_id in asset_ids if asset_id in asset_map]
    if not assets:
        return {
            "as_of": today.isoformat(),
            "base_currency": "BRL",
            "earliest_date": earliest.isoformat() if earliest else None,
            "range": range_key,
            "start_date": start_date.isoformat(),
            "series": [],
        }

    ensure_history_for_assets(db, assets, start_date, today)
    db.flush()

    prices_by_asset: Dict[int, List[AssetPrice]] = defaultdict(list)
    if asset_ids:
        rows = (
            db.query(AssetPrice)
            .filter(
                AssetPrice.asset_id.in_(list(asset_ids)),
                AssetPrice.date >= start_date,
                AssetPrice.date <= today,
            )
            .order_by(AssetPrice.asset_id.asc(), AssetPrice.date.asc())
            .all()
        )
        for row in rows:
            prices_by_asset[row.asset_id].append(row)

    previous_price_map: Dict[int, Optional[AssetPrice]] = {}
    for asset_id in asset_ids:
        prev_row = (
            db.query(AssetPrice)
            .filter(
                AssetPrice.asset_id == asset_id,
                AssetPrice.date < start_date,
            )
            .order_by(AssetPrice.date.desc())
            .first()
        )
        if prev_row:
            previous_price_map[asset_id] = prev_row

    pnl_tracker = RealizedPnlTracker()
    qty_state: Dict[int, float] = pnl_tracker.qty_state
    for asset_id in asset_ids:
        qty_state.setdefault(asset_id, 0.0)
    price_state: Dict[int, Optional[float]] = {asset_id: None for asset_id in asset_ids}
    price_pointers: Dict[int, int] = {asset_id: 0 for asset_id in asset_ids}
    invested_cumulative = 0.0
    realized_cumulative = 0.0
    fx_cache: Dict[str, tuple[float, Optional[datetime]]] = {}

    # Transa????es anteriores ao per??odo selecionado
    tx_map: Dict[date, List[Tuple[Transaction, float, bool]]] = defaultdict(list)
    for tx in transactions:
        if not tx.executed_at:
            continue
        tx_date = tx.executed_at.date()
        tx_type = (tx.type or "").lower()
        if tx_type not in {"buy", "sell"}:
            continue
        asset_id = tx.asset_id
        if asset_id is None:
            continue
        quantity = float(tx.quantity)
        if quantity <= 0:
            continue
        sign = -1.0 if tx_type == "sell" else 1.0
        tx_kind = (tx.kind or "trade").lower()
        raw_total = float(tx.total)
        delta_val = 0.0 if tx_kind == "adjust" else sign * raw_total
        realized_flag = tx_kind == "trade"
        if tx_date < start_date:
            pnl_tracker.apply(tx, count_realized=realized_flag)
            invested_cumulative += delta_val
            realized_cumulative = pnl_tracker.realized_total
        else:
            tx_map[tx_date].append((tx, delta_val, realized_flag))

    for asset_id, prev_row in previous_price_map.items():
        if prev_row is None:
            continue
        asset = asset_map.get(asset_id)
        if not asset:
            continue
        converted_price, _, _, _ = convert_to_brl(
            float(prev_row.close),
            asset.currency,
            fx_cache,
        )
        price_state[asset_id] = converted_price

    total_days = (today - start_date).days
    if total_days < 0:
        total_days = 0

    series: List[dict] = []
    for offset in range(total_days + 1):
        current_date = start_date + timedelta(days=offset)

        # Atualiza preços até a data atual
        for asset_id in asset_ids:
            asset = asset_map.get(asset_id)
            if not asset:
                continue
            rows = prices_by_asset.get(asset_id, [])
            pointer = price_pointers[asset_id]
            while pointer < len(rows) and rows[pointer].date <= current_date:
                converted_price, _, _, _ = convert_to_brl(
                    float(rows[pointer].close),
                    asset.currency,
                    fx_cache,
                )
                price_state[asset_id] = converted_price
                pointer += 1
            price_pointers[asset_id] = pointer

        # Aplica transa????es do dia
        if current_date in tx_map:
            for tx, delta_val, realized_flag in tx_map[current_date]:
                invested_cumulative += delta_val
                pnl_tracker.apply(tx, count_realized=realized_flag)
            realized_cumulative = pnl_tracker.realized_total

        market_value = 0.0

        market_value = 0.0
        for asset_id in asset_ids:
            qty = qty_state.get(asset_id, 0.0)
            price_brl = price_state.get(asset_id)
            if qty <= 0 or price_brl is None:
                continue
            market_value += qty * price_brl

        pnl_total = market_value - invested_cumulative
        pnl_unrealized = pnl_total - realized_cumulative
        series.append(
            {
                "date": current_date.isoformat(),
                "market_value": round(market_value, 2),
                "invested": round(invested_cumulative, 2),
                "pnl": round(pnl_total, 2),
                "pnl_total": round(pnl_total, 2),
                "pnl_realized": round(realized_cumulative, 2),
                "pnl_unrealized": round(pnl_unrealized, 2),
            }
        )

    return {
        "as_of": series[-1]["date"] if series else today.isoformat(),
        "base_currency": "BRL",
        "earliest_date": earliest.isoformat() if earliest else None,
        "range": range_key,
        "start_date": start_date.isoformat(),
        "series": series,
    }


@router.get("/summary")
def portfolio_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # portfolio padrao
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id)
        .order_by(Portfolio.id.asc())
        .first()
    )
    if not portfolio:
        return {
            "total": 0.0,
            "invested_total": 0.0,
            "market_total": 0.0,
            "pnl_abs": 0.0,
            "pnl_pct": 0.0,
            "day_change_abs": 0.0,
            "day_change_pct": 0.0,
            "as_of": None,
            "base_currency": "BRL",
            "kpis": {
                "invested_total": 0.0,
                "market_total": 0.0,
                "pnl_abs": 0.0,
                "pnl_pct": 0.0,
                "day_change_abs": 0.0,
                "day_change_pct": 0.0,
                "dividends_ytd": 0.0,
            },
            "itens": [],
        }

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.portfolio_id == portfolio.id,
            Transaction.status == "active",
        )
        .order_by(Transaction.executed_at.asc(), Transaction.id.asc())
        .all()
    )

    itens, invested_total, market_total, previous_total, fx_meta, as_of = (
        _build_portfolio_snapshot(db, portfolio)
    )

    pnl_tracker = RealizedPnlTracker()
    for tx in transactions:
        tx_kind = (tx.kind or "trade").lower()
        count_realized = tx_kind == "trade"
        pnl_tracker.apply(tx, count_realized=count_realized)

    realized_abs = pnl_tracker.realized_total
    realized_basis = pnl_tracker.realized_cost_basis
    unrealized_abs = market_total - invested_total
    unrealized_pct = (
        (unrealized_abs / invested_total * 100.0) if invested_total > 0 else 0.0
    )
    total_pnl_abs = realized_abs + unrealized_abs
    total_cost_basis = realized_basis + invested_total
    pnl_pct = (
        (total_pnl_abs / total_cost_basis * 100.0) if total_cost_basis > 0 else 0.0
    )
    realized_pct = (
        (realized_abs / realized_basis * 100.0) if realized_basis > 0 else 0.0
    )
    day_change_total = market_total - previous_total
    day_change_pct_total = (
        (day_change_total / previous_total * 100.0) if previous_total > 0 else 0.0
    )
    dividends_ytd = 0.0

    return {
        "total": round(market_total, 2),
        "invested_total": round(invested_total, 2),
        "market_total": round(market_total, 2),
        "pnl_abs": round(total_pnl_abs, 2),
        "pnl_pct": round(pnl_pct, 2),
        "pnl_unrealized_abs": round(unrealized_abs, 2),
        "pnl_unrealized_pct": round(unrealized_pct, 2),
        "pnl_realized_abs": round(realized_abs, 2),
        "pnl_realized_pct": round(realized_pct, 2),
        "day_change_abs": round(day_change_total, 2),
        "day_change_pct": round(day_change_pct_total, 2),
        "as_of": as_of.isoformat() if as_of else None,
        "base_currency": "BRL",
        "kpis": {
            "invested_total": round(invested_total, 2),
            "market_total": round(market_total, 2),
            "pnl_abs": round(total_pnl_abs, 2),
            "pnl_pct": round(pnl_pct, 2),
            "pnl_unrealized_abs": round(unrealized_abs, 2),
            "pnl_unrealized_pct": round(unrealized_pct, 2),
            "pnl_realized_abs": round(realized_abs, 2),
            "pnl_realized_pct": round(realized_pct, 2),
            "day_change_abs": round(day_change_total, 2),
            "day_change_pct": round(day_change_pct_total, 2),
            "dividends_ytd": round(dividends_ytd, 2),
        },
        "itens": [
            {
                **item,
                "pnl_abs": round(item["pnl_abs"], 2),
                "pnl_pct": round(item["pnl_pct"], 2),
                "day_change_abs": round(item["day_change_abs"], 2),
                "day_change_pct": round(item["day_change_pct"], 2),
                "valor": round(item["valor"], 2),
                "valor_prev": round(item["valor_prev"], 2),
            }
            for item in itens
        ],
        "fx_rates": fx_meta,
    }


@router.get("/timeseries")
def portfolio_timeseries(
    range: str = Query("6M"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    range_key = (range or "6M").upper()
    if range_key not in SERIES_RANGE_CHOICES:
        raise HTTPException(
            status_code=422,
            detail=f"Intervalo invalido. Use um de: {', '.join(sorted(SERIES_RANGE_CHOICES))}",
        )

    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id)
        .order_by(Portfolio.id.asc())
        .first()
    )
    if not portfolio:
        return {
            "as_of": None,
            "base_currency": "BRL",
            "earliest_date": None,
            "range": range_key,
            "start_date": None,
            "series": [],
        }

    holdings = (
        db.query(Holding)
        .options(joinedload(Holding.asset))
        .filter(Holding.portfolio_id == portfolio.id)
        .all()
    )

    return _generate_portfolio_timeseries(db, portfolio, holdings, range_key)


@router.get("/allocation")
def portfolio_allocation(
    mode: str = Query("class", pattern="^(class|asset)$"),
    class_filter: Optional[str] = Query(None, alias="class"),
    group_small: float = Query(0.02, ge=0.0, le=0.2),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # portfolio padrao
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id)
        .order_by(Portfolio.id.asc())
        .first()
    )
    if not portfolio:
        return {
            "mode": mode,
            "total": 0.0,
            "as_of": None,
            "base_currency": "BRL",
            "items": [],
            "available_classes": [],
        }

    itens, _, market_total, _, _, as_of = _build_portfolio_snapshot(db, portfolio)
    if market_total <= 0:
        return {
            "mode": mode,
            "total": 0.0,
            "as_of": as_of.isoformat() if as_of else None,
            "base_currency": "BRL",
            "items": [],
            "available_classes": sorted({item["class"] for item in itens}),
        }

    available_classes = sorted({item["class"] for item in itens})
    normalized_filter = normalize_class(class_filter) if class_filter else None

    if mode == "class":
        buckets: Dict[str, float] = defaultdict(float)
        for item in itens:
            buckets[item["class"]] += item["valor"]

        items_payload = [
            {
                "class": cls,
                "value": round(value, 2),
                "weight_pct": round((value / market_total) * 100.0, 2),
            }
            for cls, value in buckets.items()
        ]
        items_payload.sort(key=lambda x: x["value"], reverse=True)
        applied_filter = None
    else:
        filtered_items = (
            [item for item in itens if item["class"] == normalized_filter]
            if normalized_filter
            else itens
        )
        if not filtered_items:
            raise HTTPException(
                status_code=404,
                detail="Nenhum ativo encontrado para a classe informada.",
            )

        payload = [
            {
                "holding_id": item["holding_id"],
                "symbol": item["symbol"],
                "name": item["name"],
                "class": item["class"],
                "value": round(item["valor"], 2),
                "weight_pct": round((item["valor"] / market_total) * 100.0, 2),
            }
            for item in filtered_items
        ]
        payload.sort(key=lambda x: x["value"], reverse=True)

        threshold = max(group_small, 0.0)
        major: List[dict] = []
        grouped_value = 0.0
        for entry in payload:
            if threshold > 0 and (entry["weight_pct"] / 100.0) < threshold:
                grouped_value += entry["value"]
            else:
                major.append(entry)

        if grouped_value > 0:
            major.append(
                {
                    "holding_id": None,
                    "symbol": "OUTROS",
                    "name": "Outros",
                    "class": normalized_filter or "outros",
                    "value": round(grouped_value, 2),
                    "weight_pct": round((grouped_value / market_total) * 100.0, 2),
                }
            )

        items_payload = major
        applied_filter = normalized_filter

    return {
        "mode": mode,
        "total": round(market_total, 2),
        "as_of": as_of.isoformat() if as_of else None,
        "base_currency": "BRL",
        "items": items_payload,
        "available_classes": available_classes,
        "applied_class": applied_filter,
        "group_small": group_small,
    }


@router.get("/transactions")
def portfolio_transactions(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    status: str = Query("active", pattern="^(active|voided|all)$"),
    kind: str = Query("all"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if start and end and start > end:
        raise HTTPException(
            status_code=422, detail="Data inicial maior que a data final."
        )

    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id)
        .order_by(Portfolio.id.asc())
        .first()
    )
    if not portfolio:
        return {"items": [], "total": 0, "limit": limit, "offset": offset}

    query = (
        db.query(Transaction)
        .options(joinedload(Transaction.asset))
        .filter(Transaction.portfolio_id == portfolio.id)
    )

    status = status.lower()
    if status != "all":
        query = query.filter(Transaction.status == status)

    if start:
        start_dt = datetime.combine(start, datetime.min.time())
        query = query.filter(Transaction.executed_at >= start_dt)
    if end:
        end_dt = datetime.combine(end, datetime.max.time())
        query = query.filter(Transaction.executed_at <= end_dt)

    kind = (kind or "all").lower()
    if kind != "all":
        query = query.filter(Transaction.kind == kind)

    total = query.count()

    if order == "asc":
        query = query.order_by(Transaction.executed_at.asc(), Transaction.id.asc())
    else:
        query = query.order_by(Transaction.executed_at.desc(), Transaction.id.desc())

    rows = query.offset(offset).limit(limit).all()
    items = [serialize_transaction(tx) for tx in rows]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "order": order,
        "status": status,
        "kind": kind,
    }


@router.patch("/transactions/{tx_id}")
def update_transaction(
    tx_id: int,
    body: TransactionUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id)
        .order_by(Portfolio.id.asc())
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio nao encontrado.")

    tx = (
        db.query(Transaction)
        .options(joinedload(Transaction.asset))
        .filter(Transaction.id == tx_id, Transaction.portfolio_id == portfolio.id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transacao nao encontrada.")
    if tx.status != "active":
        raise HTTPException(
            status_code=409, detail="Nao e possivel editar uma transacao anulada."
        )

    if body.type is not None:
        tx.type = body.type.lower()

    if body.kind is not None:
        tx.kind = body.kind.lower()

    if body.quantity is not None:
        tx.quantity = float(body.quantity)

    if body.price is not None:
        tx.price = float(body.price)

    if body.executed_at is not None:
        exec_dt = body.executed_at
        if exec_dt.tzinfo is not None:
            exec_dt = exec_dt.astimezone(timezone.utc).replace(tzinfo=None)
        tx.executed_at = exec_dt

    if body.note is not None:
        note = body.note.strip()
        tx.note = note or None

    # Recalcula total com base nos valores atuais
    tx.total = float(tx.price) * float(tx.quantity)
    tx.source = "manual"

    db.commit()
    db.refresh(tx)
    return serialize_transaction(tx)


@router.post("/transactions/{tx_id}/void")
def void_transaction(
    tx_id: int,
    body: TransactionVoidRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id)
        .order_by(Portfolio.id.asc())
        .first()
    )
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio nao encontrado.")

    tx = (
        db.query(Transaction)
        .options(joinedload(Transaction.asset))
        .filter(Transaction.id == tx_id, Transaction.portfolio_id == portfolio.id)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transacao nao encontrada.")
    if tx.status == "voided":
        return serialize_transaction(tx)

    note = body.note.strip() if body.note else ""
    if note:
        tx.note = note

    tx.status = "voided"
    tx.source = "manual"

    db.commit()
    db.refresh(tx)
    return serialize_transaction(tx)


@router.get("/rebalance")
def portfolio_rebalance(
    profile_override: Optional[str] = Query(
        None,
        description="Força um perfil específico (conservador|moderado|arrojado).",
    ),
    allow_sells: bool = Query(
        True,
        description="Permite sugerir vendas para financiar compras.",
    ),
    prefer_etfs: bool = Query(
        False,
        description="Quando possível, prioriza ETFs na alocação de compras.",
    ),
    min_trade_value: float = Query(
        100.0,
        ge=0.0,
        description="Valor mínimo por ordem sugerida (em BRL).",
    ),
    max_turnover: float = Query(
        0.25,
        ge=0.0,
        le=1.0,
        description="Turnover máximo permitido (percentual do valor total).",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rp, allocation, profile_source, rules_applied = _resolve_profile_context(
        db, user.id, profile_override
    )

    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id)
        .order_by(Portfolio.id.asc())
        .first()
    )

    options_payload = {
        "allow_sells": allow_sells,
        "prefer_etfs": prefer_etfs,
        "min_trade_value": min_trade_value,
        "max_turnover": max_turnover,
    }
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    if not portfolio:
        return {
            "profile": allocation.profile,
            "profile_source": profile_source,
            "total_value": 0.0,
            "total_value_after": 0.0,
            "targets": allocation.weights,
            "bands": allocation.bands,
            "classes": {},
            "suggestions": [],
            "within_bands": True,
            "turnover": 0.0,
            "net_cash_flow": 0.0,
            "rules_applied": rules_applied,
            "notes": ["Nenhum portfólio encontrado para o usuário."],
            "as_of": timestamp_iso,
            "options": options_payload,
        }

    rows = (
        db.query(Holding)
        .options(joinedload(Holding.asset))
        .filter(Holding.portfolio_id == portfolio.id)
        .all()
    )

    if not rows:
        return {
            "profile": allocation.profile,
            "profile_source": profile_source,
            "total_value": 0.0,
            "total_value_after": 0.0,
            "targets": allocation.weights,
            "bands": allocation.bands,
            "classes": {},
            "suggestions": [],
            "within_bands": True,
            "turnover": 0.0,
            "net_cash_flow": 0.0,
            "rules_applied": rules_applied,
            "notes": ["Nenhuma posição cadastrada na carteira."],
            "as_of": timestamp_iso,
            "options": options_payload,
        }

    fx_cache: Dict[str, tuple[float, Optional[datetime]]] = {}
    holdings: List[HoldingSnapshot] = []
    total_value = 0.0

    for h in rows:
        asset = h.asset
        normalized_class = normalize_asset_class(asset.symbol, asset.class_)

        if asset.last_quote_price is not None:
            raw_price = float(asset.last_quote_price)
        else:
            last_price_row = (
                db.query(AssetPrice)
                .filter(AssetPrice.asset_id == h.asset_id)
                .order_by(AssetPrice.date.desc())
                .first()
            )
            raw_price = (
                float(last_price_row.close) if last_price_row else float(h.avg_price)
            )

        converted_price, _, _, _ = convert_to_brl(raw_price, asset.currency, fx_cache)
        value = float(h.quantity) * converted_price
        if value <= 0:
            continue

        holdings.append(
            HoldingSnapshot(
                symbol=asset.symbol,
                name=asset.name or asset.symbol,
                asset_class=normalized_class,
                quantity=float(h.quantity),
                price=converted_price,
                value=value,
                lot_size=float(asset.lot_size or 1.0),
                qty_step=float(asset.qty_step or 1.0),
                supports_fractional=bool(
                    asset.supports_fractional
                    if asset.supports_fractional is not None
                    else True
                ),
            )
        )
        total_value += value

    if total_value <= 0 or not holdings:
        return {
            "profile": allocation.profile,
            "profile_source": profile_source,
            "total_value": 0.0,
            "total_value_after": 0.0,
            "targets": allocation.weights,
            "bands": allocation.bands,
            "classes": {},
            "suggestions": [],
            "within_bands": True,
            "turnover": 0.0,
            "net_cash_flow": 0.0,
            "rules_applied": rules_applied,
            "notes": ["Não há valores positivos para rebalancear."],
            "as_of": timestamp_iso,
            "options": options_payload,
        }

    options = RebalanceOptions(
        allow_sells=allow_sells,
        min_trade_value=min_trade_value,
        max_turnover=max_turnover,
        prefer_etfs=prefer_etfs,
    )

    result = rebalance_portfolio(
        holdings, allocation.weights, allocation.bands, options
    )

    class_payload: Dict[str, dict] = {}
    for cls, summary in result.class_summaries.items():
        class_payload[cls] = {
            "label": CLASS_LABELS.get(cls, cls.title()),
            "current_value": summary.current_value,
            "current_pct": round(summary.current_pct, 6),
            "target_pct": round(summary.target_pct, 6),
            "floor_pct": round(summary.floor_pct, 6),
            "ceiling_pct": round(summary.ceiling_pct, 6),
            "delta_value": summary.delta_value,
            "post_value": summary.post_value,
            "post_pct": round(summary.post_pct, 6),
            "delta_pct": round(summary.post_pct - summary.current_pct, 6),
        }

    suggestions_payload = [
        {
            "symbol": s.symbol,
            "class": s.asset_class,
            "action": s.action,
            "quantity": s.quantity,
            "value": s.value,
            "price_ref": s.price_ref,
            "weight_before": round(s.weight_before, 6),
            "weight_after": round(s.weight_after, 6),
            "class_weight_before": round(s.class_weight_before, 6),
            "class_weight_after": round(s.class_weight_after, 6),
            "rationale": s.rationale,
        }
        for s in result.suggestions
    ]

    total_after = total_value + result.net_cash_flow
    notes = list(result.notes)
    if not notes and not suggestions_payload:
        notes.append("Carteira já dentro das bandas definidas.")

    candidates_payload: Dict[str, List[dict]] = {}
    for cls in result.missing_buy_classes:
        suggestions = CLASS_CANDIDATES.get(cls)
        if not suggestions:
            continue
        class_label = CLASS_LABELS.get(cls, cls.title())
        candidates_payload[cls] = [
            {
                "symbol": item["symbol"],
                "description": item.get("description"),
                "class": cls,
                "class_label": class_label,
            }
            for item in suggestions
        ]

    return {
        "profile": allocation.profile,
        "profile_source": profile_source,
        "score": rp.score if rp else None,
        "total_value": round(total_value, 2),
        "total_value_after": round(total_after, 2),
        "targets": allocation.weights,
        "bands": allocation.bands,
        "classes": class_payload,
        "suggestions": suggestions_payload,
        "within_bands": result.within_bands,
        "turnover": round(result.turnover, 4),
        "net_cash_flow": result.net_cash_flow,
        "rules_applied": rules_applied,
        "notes": notes,
        "as_of": result.priced_at.isoformat(),
        "options": options_payload,
        "candidates": candidates_payload,
    }


@router.post("/rebalance/apply")
def portfolio_rebalance_apply(
    body: RebalanceApplyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not body.suggestions:
        raise HTTPException(status_code=422, detail="Nenhuma sugestão selecionada.")

    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id)
        .order_by(Portfolio.id.asc())
        .first()
    )
    if not portfolio:
        raise HTTPException(
            status_code=400, detail="Nenhum portfólio cadastrado para aplicar ajustes."
        )

    options = body.options
    current_plan = portfolio_rebalance(
        profile_override=options.profile_override,
        allow_sells=options.allow_sells,
        prefer_etfs=options.prefer_etfs,
        min_trade_value=options.min_trade_value,
        max_turnover=options.max_turnover,
        db=db,
        user=user,
    )

    plan_suggestions = current_plan.get("suggestions") or []
    if not plan_suggestions:
        raise HTTPException(
            status_code=422, detail="Nenhuma sugestão disponível para aplicar."
        )

    plan_index: Dict[tuple[str, str], dict] = {}
    for item in plan_suggestions:
        key = (item["symbol"].upper(), item["action"])
        plan_index[key] = item

    to_apply: List[dict] = []
    EPS = 1e-4
    for suggestion in body.suggestions:
        key = (suggestion.symbol.upper(), suggestion.action)
        plan_item = plan_index.get(key)
        if not plan_item:
            raise HTTPException(
                status_code=422,
                detail=f"Sugestão para {suggestion.symbol} não encontrada ou desatualizada.",
            )
        if abs(plan_item["quantity"] - float(suggestion.quantity)) > EPS:
            raise HTTPException(
                status_code=422,
                detail=f"Quantidade divergente para {suggestion.symbol}. Recalcule o rebalanceamento.",
            )
        to_apply.append(plan_item)

    request_marker = f"rebalance::{body.request_id.strip()}"
    existing_tx = (
        db.query(Transaction.id)
        .filter(
            Transaction.portfolio_id == portfolio.id,
            Transaction.source == "rebalance",
            Transaction.note == request_marker,
        )
        .first()
    )
    if existing_tx:
        raise HTTPException(
            status_code=409, detail="Já existe uma aplicação para este request_id."
        )

    rows = (
        db.query(Holding)
        .options(joinedload(Holding.asset))
        .filter(Holding.portfolio_id == portfolio.id)
        .all()
    )
    holdings_by_symbol = {row.asset.symbol.upper(): row for row in rows if row.asset}
    assets_by_symbol = {
        row.asset.symbol.upper(): row.asset for row in rows if row.asset
    }

    applied_records: List[dict] = []
    base_date = body.execution_date or datetime.now(timezone.utc).date()
    execution_dt = datetime.combine(base_date, datetime.min.time(), tzinfo=timezone.utc)
    today_utc = base_date
    now = execution_dt

    for item in to_apply:
        symbol = item["symbol"].upper()
        action = item["action"]
        qty = float(item["quantity"])
        price = float(item.get("price_ref") or item.get("price") or 0.0)
        if price <= 0:
            raise HTTPException(
                status_code=422,
                detail=f"Preço inválido para {symbol}. Recalcule o rebalanceamento.",
            )

        holding = holdings_by_symbol.get(symbol)
        asset = assets_by_symbol.get(symbol)
        if not asset and holding and holding.asset:
            asset = holding.asset
            assets_by_symbol[symbol] = asset

        if not asset:
            asset = db.query(Asset).filter(Asset.symbol == symbol).first()
            if not asset:
                raise HTTPException(
                    status_code=404, detail=f"Ativo {symbol} não encontrado."
                )
            assets_by_symbol[symbol] = asset

        if action == "comprar":
            if not holding:
                holding = Holding(
                    portfolio_id=portfolio.id,
                    asset_id=asset.id,
                    quantity=0.0,
                    avg_price=price,
                    purchase_date=today_utc,
                    created_at=now.replace(tzinfo=None),
                    updated_at=now.replace(tzinfo=None),
                )
                db.add(holding)
                holdings_by_symbol[symbol] = holding
            prev_qty = float(holding.quantity)
            new_qty = prev_qty + qty
            total_cost = prev_qty * float(holding.avg_price) + qty * price
            holding.quantity = new_qty
            holding.avg_price = total_cost / new_qty if new_qty > 0 else price
            holding.updated_at = now.replace(tzinfo=None)
        else:
            if not holding:
                raise HTTPException(
                    status_code=422,
                    detail=f"Sugestão de venda para {symbol} inválida: ativo não encontrado.",
                )
            prev_qty = float(holding.quantity)
            if qty - prev_qty > EPS:
                raise HTTPException(
                    status_code=422,
                    detail=f"Quantidade disponível insuficiente para vender {symbol}.",
                )
            new_qty = prev_qty - qty
            if new_qty <= EPS:
                db.delete(holding)
                holdings_by_symbol.pop(symbol, None)
            else:
                holding.quantity = new_qty
                holding.updated_at = now.replace(tzinfo=None)

        record_transaction(
            db,
            portfolio.id,
            asset.id,
            "buy" if action == "comprar" else "sell",
            qty,
            price,
            executed_at=now,
            kind="adjust",
            source="rebalance",
            note=request_marker,
        )
        applied_records.append(
            {"symbol": symbol, "action": action, "quantity": qty, "price": price}
        )

    db.commit()

    updated_plan = portfolio_rebalance(
        profile_override=options.profile_override,
        allow_sells=options.allow_sells,
        prefer_etfs=options.prefer_etfs,
        min_trade_value=options.min_trade_value,
        max_turnover=options.max_turnover,
        db=db,
        user=user,
    )

    return {
        "status": "applied",
        "request_id": body.request_id,
        "applied": len(applied_records),
        "transactions": applied_records,
        "result": updated_plan,
    }

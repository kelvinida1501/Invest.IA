from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from collections import defaultdict
from typing import Dict, List
from math import isfinite

from app.db.base import get_db
from app.db.models import (
    Holding,
    Portfolio,
    AssetPrice,
    RiskProfile,  # <- necessário no rebalance
)
from app.routes.auth import get_current_user, User  # type: ignore

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def latest_close_for(db: Session, asset_id: int):
    return (
        db.query(AssetPrice)
        .filter(AssetPrice.asset_id == asset_id)
        .order_by(AssetPrice.date.desc())
        .first()
    )


@router.get("/summary")
def portfolio_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # portfolio padrão
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
            "itens": [],
        }

    rows = (
        db.query(Holding)
        .options(joinedload(Holding.asset))
        .filter(Holding.portfolio_id == portfolio.id)
        .all()
    )

    itens = []
    invested_total = 0.0
    market_total = 0.0

    for h in rows:
        a = h.asset
        inv = float(h.quantity) * float(h.avg_price)
        invested_total += inv

        last = latest_close_for(db, h.asset_id)
        last_price = float(last.close) if last else float(h.avg_price)
        valor = float(h.quantity) * last_price
        market_total += valor

        itens.append(
            {
                "holding_id": h.id,
                "asset_id": h.asset_id,
                "symbol": a.symbol,
                "name": a.name,
                "class": a.class_,
                "quantity": float(h.quantity),
                "avg_price": float(h.avg_price),
                "last_price": last_price,
                "valor": valor,
                "pct": 0.0,
            }
        )

    total = market_total
    if total > 0:
        for i in itens:
            i["pct"] = round((i["valor"] / total) * 100.0, 2)

    pnl_abs = market_total - invested_total
    pnl_pct = (pnl_abs / invested_total * 100.0) if invested_total > 0 else 0.0

    return {
        "total": round(total, 2),
        "invested_total": round(invested_total, 2),
        "market_total": round(market_total, 2),
        "pnl_abs": round(pnl_abs, 2),
        "pnl_pct": round(pnl_pct, 2),
        "itens": itens,
    }


@router.get("/rebalance")
def portfolio_rebalance(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    profile_override: str | None = None,
):
    # 1) Perfil
    rp = db.query(RiskProfile).filter(RiskProfile.user_id == user.id).first()
    profile = (profile_override or (rp.profile if rp else None)) or "moderado"

    # 2) Targets por perfil (somam 1.0)
    targets_map: Dict[str, Dict[str, float]] = {
        "conservador": {"acao": 0.30, "etf": 0.00, "fundo": 0.60, "cripto": 0.10},
        "moderado": {"acao": 0.45, "etf": 0.10, "fundo": 0.35, "cripto": 0.10},
        "arrojado": {"acao": 0.60, "etf": 0.15, "fundo": 0.15, "cripto": 0.10},
    }
    targets = targets_map.get(profile, targets_map["moderado"])

    # 3) Portfolio padrão
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.user_id == user.id)
        .order_by(Portfolio.id.asc())
        .first()
    )
    if not portfolio:
        return {
            "profile": profile,
            "total": 0.0,
            "targets": targets,
            "suggestions": [],
            "buckets": {"values": {}, "pct": {}},
        }

    rows = (
        db.query(Holding)
        .options(joinedload(Holding.asset))
        .filter(Holding.portfolio_id == portfolio.id)
        .all()
    )
    if not rows:
        return {
            "profile": profile,
            "total": 0.0,
            "targets": targets,
            "suggestions": [],
            "buckets": {"values": {}, "pct": {}},
        }

    # 4) Preço
    def last_price_for(asset_id: int, fallback: float) -> float:
        p = (
            db.query(AssetPrice)
            .filter(AssetPrice.asset_id == asset_id)
            .order_by(AssetPrice.date.desc())
            .first()
        )
        return float(p.close) if p else float(fallback)

    # 5) Agrega por bucket
    bucket_vals: Dict[str, float] = defaultdict(float)
    items: List[dict] = []
    total = 0.0

    for h in rows:
        a = h.asset
        cls = (a.class_ or "acao").lower()
        if cls not in ("acao", "etf", "fundo", "cripto"):
            cls = "acao"

        lp = last_price_for(h.asset_id, float(h.avg_price))
        val = float(h.quantity) * lp
        total += val
        bucket_vals[cls] += val

        items.append(
            {
                "holding_id": h.id,
                "symbol": a.symbol,
                "class": cls,
                "qty": float(h.quantity),
                "last_price": lp,
                "valor": val,
            }
        )

    if total <= 0:
        return {
            "profile": profile,
            "total": 0.0,
            "targets": targets,
            "suggestions": [],
            "buckets": {"values": {}, "pct": {}},
        }

    # 6) Valor-alvo por bucket
    target_values = {k: total * v for k, v in targets.items()}

    # 7) Totais por bucket para distribuir proporcionalmente
    bucket_totals = defaultdict(float)
    for it in items:
        bucket_totals[it["class"]] += it["valor"]

    suggestions = []
    for it in items:
        b = it["class"]
        bt = bucket_totals[b]
        if bt <= 0:
            continue
        desired_val_in_bucket = target_values.get(b, 0.0)
        weight = it["valor"] / bt
        desired_val_for_asset = desired_val_in_bucket * weight
        delta_val = desired_val_for_asset - it["valor"]
        delta_qty = delta_val / it["last_price"] if it["last_price"] > 0 else 0.0

        if abs(delta_val) < 1e-2 or not isfinite(delta_qty):
            continue

        suggestions.append(
            {
                "symbol": it["symbol"],
                "class": b,
                "action": "comprar" if delta_val > 0 else "vender",
                "delta_value": round(delta_val, 2),
                "delta_qty": round(delta_qty, 4),
                "price_ref": round(it["last_price"], 2),
            }
        )

    suggestions.sort(key=lambda s: abs(s["delta_value"]), reverse=True)

    # 8) Converte defaultdict -> dict (JSON serializável) e arredonda
    values_dict = {k: round(v, 2) for k, v in bucket_vals.items()}
    # garante que todos os buckets-alvo existam no retorno
    for k in targets.keys():
        values_dict.setdefault(k, 0.0)

    buckets_pct = {
        k: round((values_dict[k] / total) * 100.0, 2) if total > 0 else 0.0
        for k in values_dict.keys()
    }

    return {
        "profile": profile,
        "total": round(total, 2),
        "targets": targets,
        "buckets": {"values": values_dict, "pct": buckets_pct},
        "suggestions": suggestions,
    }

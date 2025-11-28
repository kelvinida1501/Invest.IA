from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Dict, List, Sequence, Tuple


@dataclass
class HoldingSnapshot:
    symbol: str
    name: str
    asset_class: str
    quantity: float
    price: float
    value: float
    lot_size: float = 1.0
    qty_step: float = 1.0
    supports_fractional: bool = True


@dataclass
class RebalanceOptions:
    allow_sells: bool = True
    min_trade_value: float = 100.0
    max_turnover: float = 0.25  # percentual do valor total
    prefer_etfs: bool = False


@dataclass
class Suggestion:
    symbol: str
    asset_class: str
    action: str  # comprar|vender
    quantity: float
    value: float
    price_ref: float
    weight_before: float
    weight_after: float
    class_weight_before: float
    class_weight_after: float
    rationale: str


@dataclass
class ClassSummary:
    current_value: float
    current_pct: float
    target_pct: float
    floor_pct: float
    ceiling_pct: float
    delta_value: float
    post_value: float
    post_pct: float


@dataclass
class RebalanceResult:
    holdings: Sequence[HoldingSnapshot]
    class_summaries: Dict[str, ClassSummary]
    suggestions: Sequence[Suggestion]
    within_bands: bool
    turnover: float
    net_cash_flow: float
    priced_at: datetime
    notes: Sequence[str]
    missing_buy_classes: Sequence[str]


def _round_quantity(target_qty: float, snapshot: HoldingSnapshot) -> float:
    if abs(target_qty) < 1e-9:
        return 0.0
    if snapshot.supports_fractional:
        return round(target_qty, 6)

    step_candidates = [snapshot.qty_step, snapshot.lot_size]
    step = 1.0
    for candidate in step_candidates:
        if candidate and abs(candidate) > 0:
            step = abs(candidate)
            break

    ratio = 0.0 if step == 0 else target_qty / step
    ratio = round(ratio, 6)

    if target_qty > 0:
        steps = math.floor(ratio)
    else:
        steps = math.ceil(ratio)

    rounded = steps * step
    return 0.0 if abs(rounded) < 1e-9 else rounded


def _plan_trade(
    delta_value: float, snapshot: HoldingSnapshot, min_trade_value: float
) -> tuple[float, float] | None:
    if abs(delta_value) < 1e-9 or snapshot.price <= 0:
        return None

    target_qty = delta_value / snapshot.price
    rounded_qty = _round_quantity(target_qty, snapshot)
    if abs(rounded_qty) < 1e-9:
        return None

    executed_value = round(rounded_qty * snapshot.price, 2)
    if abs(executed_value) + 1e-9 < min_trade_value:
        return None

    return rounded_qty, executed_value


def rebalance_portfolio(
    holdings: Sequence[HoldingSnapshot],
    targets: Dict[str, float],
    bands: Dict[str, float],
    options: RebalanceOptions,
) -> RebalanceResult:
    total_value = sum(h.value for h in holdings)
    priced_at = datetime.now(timezone.utc)

    if total_value <= 0:
        return RebalanceResult(
            holdings=holdings,
            class_summaries={},
            suggestions=[],
            within_bands=True,
            turnover=0.0,
            net_cash_flow=0.0,
            priced_at=priced_at,
            notes=["Carteira vazia ou com valor total zero."],
            missing_buy_classes=[],
        )

    class_totals: Dict[str, float] = {}
    for h in holdings:
        class_totals[h.asset_class] = class_totals.get(h.asset_class, 0.0) + h.value

    # Inclui classes que existem no alvo, mesmo sem posição atual
    for cls in targets.keys():
        class_totals.setdefault(cls, 0.0)

    current_pct: Dict[str, float] = {
        cls: (val / total_value) if total_value > 0 else 0.0
        for cls, val in class_totals.items()
    }

    deltas: Dict[str, float] = {}
    deficits: List[Tuple[str, float]] = []
    surpluses: List[Tuple[str, float]] = []
    notes: List[str] = []

    for cls, target_pct in targets.items():
        current = current_pct.get(cls, 0.0)
        band = bands.get(cls, 0.0)
        delta_value = (target_pct - current) * total_value

        if abs(current - target_pct) > band + 1e-6:
            deltas[cls] = delta_value
            if delta_value > 0:
                deficits.append((cls, delta_value))
            elif delta_value < 0:
                surpluses.append((cls, -delta_value))
        else:
            deltas[cls] = 0.0

    total_buy = sum(val for _, val in deficits)
    total_sell = sum(val for _, val in surpluses)

    # Ordena deficits/surpluses por maior necessidade
    deficits.sort(key=lambda item: item[1], reverse=True)
    surpluses.sort(key=lambda item: item[1], reverse=True)

    allow_sells = options.allow_sells
    max_turnover = max(0.0, min(1.0, options.max_turnover))
    min_trade_value = max(0.0, options.min_trade_value)

    buy_budget = 0.0
    sell_budget = 0.0

    if allow_sells and total_buy > 0 and total_sell > 0:
        balanced_budget = min(total_buy, total_sell)
        max_budget = max_turnover * total_value / 2.0
        buy_budget = sell_budget = min(balanced_budget, max_budget)
        if balanced_budget > max_budget:
            notes.append("Turnover máximo atingido; parte do desvio permanece.")
    elif total_buy > 0:
        buy_budget = min(total_buy, max_turnover * total_value)
        if allow_sells:
            notes.append(
                "Sem posições excedentes suficientes; aporte externo necessário."
            )
        else:
            notes.append("Vendas desativadas; aporte externo necessário.")
        if buy_budget < total_buy:
            notes.append("Turnover máximo limitou o ajuste total.")
    elif allow_sells and total_sell > 0:
        sell_budget = min(total_sell, max_turnover * total_value)
        notes.append("Ajuste resultará em geração de caixa (redução de exposição).")
        if sell_budget < total_sell:
            notes.append("Turnover máximo limitou o ajuste total.")
    else:
        # Nada a fazer
        return RebalanceResult(
            holdings=holdings,
            class_summaries=_build_class_summaries(
                targets,
                bands,
                class_totals,
                current_pct,
                class_totals,
                total_value,
                total_value,
            ),
            suggestions=[],
            within_bands=True,
            turnover=0.0,
            net_cash_flow=0.0,
            priced_at=priced_at,
            notes=notes or ["Carteira já dentro das bandas definidas."],
            missing_buy_classes=[],
        )

    class_buy_alloc: Dict[str, float] = {cls: 0.0 for cls in class_totals}
    class_sell_alloc: Dict[str, float] = {cls: 0.0 for cls in class_totals}

    if total_buy > 0 and buy_budget > 0:
        preference_weights: Dict[str, float] = {}
        weighted_total = 0.0
        for cls, deficit_value in deficits:
            preference = 1.0
            if options.prefer_etfs and cls == "etf":
                preference = 1.3
            preference_weights[cls] = deficit_value * preference
            weighted_total += preference_weights[cls]

        if weighted_total <= 0:
            weighted_total = total_buy
            preference_weights = {cls: deficit for cls, deficit in deficits}

        for cls, deficit_value in deficits:
            weight_value = preference_weights.get(cls, deficit_value)
            class_buy_alloc[cls] = (
                (weight_value / weighted_total) * buy_budget
                if weighted_total > 0
                else 0.0
            )
    if total_sell > 0 and sell_budget > 0:
        for cls, surplus_value in surpluses:
            class_sell_alloc[cls] = (
                (surplus_value / total_sell) * sell_budget if total_sell > 0 else 0.0
            )

    delta_by_symbol: Dict[str, float] = {}

    missing_buy_classes: set[str] = set()

    # Aplica compras
    for cls, amount in class_buy_alloc.items():
        if amount <= 0:
            continue
        class_assets = [h for h in holdings if h.asset_class == cls and h.price > 0]
        if not class_assets:
            notes.append(
                f"Sem ativos cadastrados em {cls} para receber compras sugeridas."
            )
            missing_buy_classes.add(cls)
            continue
        class_total = sum(h.value for h in class_assets)
        if class_total <= 0:
            equal_share = amount / len(class_assets)
            for h in class_assets:
                delta_by_symbol[h.symbol] = (
                    delta_by_symbol.get(h.symbol, 0.0) + equal_share
                )
            continue
        for h in class_assets:
            weight = (
                h.value / class_total if class_total > 0 else 1.0 / len(class_assets)
            )
            delta_val = amount * weight
            delta_by_symbol[h.symbol] = delta_by_symbol.get(h.symbol, 0.0) + delta_val

    # Aplica vendas
    for cls, amount in class_sell_alloc.items():
        if amount <= 0:
            continue
        class_assets = [h for h in holdings if h.asset_class == cls and h.price > 0]
        if not class_assets:
            notes.append(
                f"Sem ativos cadastrados em {cls} para realizar vendas sugeridas."
            )
            continue
        class_total = sum(h.value for h in class_assets)
        if class_total <= 0:
            continue
        for h in class_assets:
            weight = (
                h.value / class_total if class_total > 0 else 1.0 / len(class_assets)
            )
            delta_val = -amount * weight
            # Garante que não vendemos mais do que a posição
            max_sell = -h.value
            if delta_val < max_sell:
                delta_val = max_sell
            delta_by_symbol[h.symbol] = delta_by_symbol.get(h.symbol, 0.0) + delta_val

    post_class_totals: Dict[str, float] = class_totals.copy()
    planned_trades: List[dict] = []
    skipped_min_trade = False

    for h in holdings:
        delta_val = delta_by_symbol.get(h.symbol, 0.0)
        trade = _plan_trade(delta_val, h, min_trade_value)
        if not trade:
            if abs(delta_val) > 1e-9:
                skipped_min_trade = True
            continue

        qty, executed_value = trade
        post_class_totals[h.asset_class] = (
            post_class_totals.get(h.asset_class, 0.0) + executed_value
        )
        planned_trades.append(
            {
                "holding": h,
                "quantity": qty,
                "value": executed_value,
                "post_value": h.value + executed_value,
            }
        )

    total_purchases = sum(plan["value"] for plan in planned_trades if plan["value"] > 0)
    total_sales = -sum(plan["value"] for plan in planned_trades if plan["value"] < 0)
    net_cash_flow_effective = round(total_purchases - total_sales, 2)

    total_after = total_value + net_cash_flow_effective
    if total_after <= 0:
        total_after = total_value  # fallback

    suggestions: List[Suggestion] = []
    for plan in planned_trades:
        h = plan["holding"]
        executed_value = plan["value"]
        qty = plan["quantity"]
        post_value = plan["post_value"]

        action = "comprar" if executed_value > 0 else "vender"
        weight_before = h.value / total_value if total_value > 0 else 0.0
        weight_after = post_value / total_after if total_after > 0 else 0.0

        class_weight_before = (
            class_totals.get(h.asset_class, 0.0) / total_value
            if total_value > 0
            else 0.0
        )
        class_weight_after = (
            post_class_totals.get(h.asset_class, 0.0) / total_after
            if total_after > 0
            else 0.0
        )

        rationale = (
            f"{'Aumentar' if action == 'comprar' else 'Reduzir'} participação em {h.asset_class} "
            f"para aproximar do alvo."
        )

        suggestions.append(
            Suggestion(
                symbol=h.symbol,
                asset_class=h.asset_class,
                action=action,
                quantity=round(abs(qty), 4),
                value=executed_value,
                price_ref=round(h.price, 4),
                weight_before=weight_before,
                weight_after=weight_after,
                class_weight_before=class_weight_before,
                class_weight_after=class_weight_after,
                rationale=rationale,
            )
        )

    suggestions.sort(key=lambda s: abs(s.value), reverse=True)

    if skipped_min_trade:
        note_msg = f"Ajustes abaixo do valor minimo por ordem (R$ {min_trade_value:,.2f}) foram ignorados."
        if note_msg not in notes:
            notes.append(note_msg)

    if allow_sells:
        turnover = (
            (abs(total_purchases) + abs(total_sales)) / total_value
            if total_value > 0
            else 0.0
        )
    else:
        turnover = abs(total_purchases) / total_value if total_value > 0 else 0.0

    class_summaries = _build_class_summaries(
        targets,
        bands,
        class_totals,
        current_pct,
        post_class_totals,
        total_value,
        total_after,
    )

    within_bands_after = True
    for cls, summary in class_summaries.items():
        if (
            summary.post_pct < summary.floor_pct - 1e-6
            or summary.post_pct > summary.ceiling_pct + 1e-6
        ):
            within_bands_after = False
            break

    return RebalanceResult(
        holdings=holdings,
        class_summaries=class_summaries,
        suggestions=suggestions,
        within_bands=within_bands_after,
        turnover=turnover,
        net_cash_flow=net_cash_flow_effective,
        priced_at=priced_at,
        notes=notes,
        missing_buy_classes=sorted(missing_buy_classes),
    )


def _build_class_summaries(
    targets: Dict[str, float],
    bands: Dict[str, float],
    class_totals_before: Dict[str, float],
    current_pct: Dict[str, float],
    class_totals_after: Dict[str, float],
    total_before: float,
    total_after: float,
) -> Dict[str, ClassSummary]:
    summaries: Dict[str, ClassSummary] = {}
    keys = set(class_totals_before.keys()) | set(targets.keys())

    for cls in keys:
        target_pct = targets.get(cls, 0.0)
        band = bands.get(cls, 0.0)
        current_value = class_totals_before.get(cls, 0.0)
        post_value = class_totals_after.get(cls, current_value)

        summaries[cls] = ClassSummary(
            current_value=round(current_value, 2),
            current_pct=current_pct.get(cls, 0.0),
            target_pct=target_pct,
            floor_pct=max(0.0, target_pct - band),
            ceiling_pct=min(1.0, target_pct + band),
            delta_value=round(post_value - current_value, 2),
            post_value=round(post_value, 2),
            post_pct=(post_value / total_after) if total_after > 0 else 0.0,
        )

    return summaries

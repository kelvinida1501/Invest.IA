from datetime import datetime
from types import SimpleNamespace

import pytest

from app.routes import portfolio as portfolio_route
from app.db.models import Transaction


FAKE_OPTIONS = {
    "allow_sells": True,
    "prefer_etfs": False,
    "min_trade_value": 50,
    "max_turnover": 0.25,
    "profile_override": None,
}


def _fake_result(symbol="PLAN1", action="comprar", quantity=1.0, price=10.0):
    return SimpleNamespace(
        class_summaries={
            "acao": SimpleNamespace(
                current_value=100.0,
                current_pct=0.5,
                target_pct=0.5,
                floor_pct=0.4,
                ceiling_pct=0.6,
                delta_value=0.0,
                post_value=100.0,
                post_pct=0.5,
            )
        },
        suggestions=[
            SimpleNamespace(
                symbol=symbol,
                asset_class="acao",
                action=action,
                quantity=quantity,
                value=price * quantity,
                price_ref=price,
                weight_before=0.5,
                weight_after=0.6,
                class_weight_before=0.5,
                class_weight_after=0.6,
                rationale="ajuste",
            )
        ],
        within_bands=False,
        turnover=0.1,
        net_cash_flow=0.0,
        notes=[],
        priced_at=datetime.utcnow(),
        missing_buy_classes=[],
    )


def test_rebalance_apply_requires_suggestions(client, user_token):
    headers, _ = user_token
    body = {
        "request_id": "req-001",
        "suggestions": [],
        "options": FAKE_OPTIONS,
    }
    resp = client.post("/api/portfolio/rebalance/apply", headers=headers, json=body)
    assert resp.status_code == 422


def test_rebalance_apply_without_portfolio_returns_400(client, user_token, monkeypatch):
    headers, _ = user_token
    monkeypatch.setattr(
        portfolio_route, "rebalance_portfolio", lambda *args, **kwargs: _fake_result()
    )
    body = {
        "request_id": "req-002",
        "suggestions": [{"symbol": "PLAN1", "action": "comprar", "quantity": 1, "price": 10}],
        "options": FAKE_OPTIONS,
    }
    resp = client.post("/api/portfolio/rebalance/apply", headers=headers, json=body)
    assert resp.status_code == 400


def test_rebalance_apply_price_must_be_positive(client, user_token, monkeypatch):
    headers, _ = user_token
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "PLAN1", "quantity": 1, "avg_price": 10}],
    )
    monkeypatch.setattr(
        portfolio_route, "rebalance_portfolio", lambda *args, **kwargs: _fake_result(price=0.0)
    )
    body = {
        "request_id": "req-003",
        "suggestions": [{"symbol": "PLAN1", "action": "comprar", "quantity": 1, "price": 0}],
        "options": FAKE_OPTIONS,
    }
    resp = client.post("/api/portfolio/rebalance/apply", headers=headers, json=body)
    assert resp.status_code == 422


def test_rebalance_apply_sell_requires_holding(client, user_token, db_session, monkeypatch):
    headers, _ = user_token
    # cria portfolio com ativo diferente para garantir portfolio existente
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "OUTRO", "quantity": 1, "avg_price": 10}],
    )
    db_session.add(
        portfolio_route.Asset(symbol="VENTA", name="Venda", currency="BRL", class_="acao")
    )
    db_session.commit()
    monkeypatch.setattr(
        portfolio_route,
        "rebalance_portfolio",
        lambda *args, **kwargs: _fake_result(symbol="VENTA", action="vender", quantity=1.0),
    )
    body = {
        "request_id": "req-004",
        "suggestions": [{"symbol": "VENTA", "action": "vender", "quantity": 1, "price": 10}],
        "options": FAKE_OPTIONS,
    }
    resp = client.post("/api/portfolio/rebalance/apply", headers=headers, json=body)
    assert resp.status_code == 422


def test_rebalance_apply_quantity_divergence(client, user_token, monkeypatch):
    headers, _ = user_token
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "PLAN1", "quantity": 1, "avg_price": 10}],
    )
    monkeypatch.setattr(
        portfolio_route,
        "rebalance_portfolio",
        lambda *args, **kwargs: _fake_result(symbol="PLAN1", action="comprar", quantity=1.0),
    )
    body = {
        "request_id": "req-005",
        "suggestions": [{"symbol": "PLAN1", "action": "comprar", "quantity": 2, "price": 10}],
        "options": FAKE_OPTIONS,
    }
    resp = client.post("/api/portfolio/rebalance/apply", headers=headers, json=body)
    assert resp.status_code == 422


def test_rebalance_apply_conflict_on_request_id(client, user_token, db_session, monkeypatch):
    headers, user = user_token
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "PLAN1", "quantity": 1, "avg_price": 10}],
    )
    monkeypatch.setattr(
        portfolio_route,
        "rebalance_portfolio",
        lambda *args, **kwargs: _fake_result(symbol="PLAN1", action="comprar", quantity=1.0),
    )
    # cria transacao existente com mesmo request_id
    portfolio_id = (
        db_session.query(portfolio_route.Portfolio.id)
        .filter_by(user_id=user.id)
        .first()[0]
    )
    asset_id = (
        db_session.query(portfolio_route.Asset.id)
        .filter_by(symbol="PLAN1")
        .scalar()
    )
    tx = Transaction(
        portfolio_id=portfolio_id,
        asset_id=asset_id,
        type="buy",
        quantity=1.0,
        price=10.0,
        total=10.0,
        note="rebalance::dup-001",
        source="rebalance",
        executed_at=datetime.utcnow(),
    )
    db_session.add(tx)
    db_session.commit()

    body = {
        "request_id": "dup-001",
        "suggestions": [{"symbol": "PLAN1", "action": "comprar", "quantity": 1, "price": 10}],
        "options": FAKE_OPTIONS,
    }
    resp = client.post("/api/portfolio/rebalance/apply", headers=headers, json=body)
    assert resp.status_code == 409

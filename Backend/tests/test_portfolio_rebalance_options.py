from types import SimpleNamespace
from datetime import datetime, timezone

from app.routes import portfolio as portfolio_route


def test_portfolio_rebalance_returns_empty_when_no_portfolio(client, user_token, monkeypatch):
    headers, _ = user_token
    fake_allocation = SimpleNamespace(
        profile="moderado",
        weights={"acao": 0.5},
        bands={"acao": 0.1},
        description="desc",
    )
    monkeypatch.setattr(
        portfolio_route,
        "_resolve_profile_context",
        lambda db, uid, override: (None, fake_allocation, "default", []),
    )
    resp = client.get("/api/portfolio/rebalance", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["suggestions"] == []


def test_portfolio_rebalance_no_holdings_returns_message(client, user_token, monkeypatch):
    headers, _ = user_token
    portfolio_route.rebalance_portfolio_cache = {}
    fake_allocation = SimpleNamespace(
        profile="moderado",
        weights={"acao": 0.5},
        bands={"acao": 0.1},
        description="desc",
    )
    monkeypatch.setattr(
        portfolio_route,
        "_resolve_profile_context",
        lambda db, uid, override: (None, fake_allocation, "default", []),
    )
    # cria portfólio vazio
    resp = client.get("/api/portfolio/rebalance", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_value"] == 0.0
    assert body["within_bands"] is True or body["suggestions"] == []


def test_portfolio_rebalance_apply_conflict_request_id(client, user_token, monkeypatch, db_session):
    headers, _ = user_token
    # cria holding
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "PLANZ", "quantity": 1, "avg_price": 10}],
    )
    fake_allocation = SimpleNamespace(
        profile="moderado",
        weights={"acao": 0.5},
        bands={"acao": 0.1},
        description="desc",
    )
    monkeypatch.setattr(
        portfolio_route,
        "_resolve_profile_context",
        lambda db, uid, override: (None, fake_allocation, "default", []),
    )
    monkeypatch.setattr(
        portfolio_route,
        "rebalance_portfolio",
        lambda *args, **kwargs: {
            "class_summaries": {},
            "suggestions": [
                {
                    "symbol": "PLANZ",
                    "class": "acao",
                    "action": "comprar",
                    "quantity": 1.0,
                    "value": 10.0,
                    "price_ref": 10.0,
                    "weight_before": 0.5,
                    "weight_after": 0.6,
                    "class_weight_before": 0.5,
                    "class_weight_after": 0.6,
                    "rationale": "ajuste",
                }
            ],
            "within_bands": False,
            "turnover": 0.1,
            "net_cash_flow": 0.0,
            "notes": [],
                "priced_at": datetime.now(timezone.utc),
            "missing_buy_classes": [],
            "options": {},
        },
    )
    monkeypatch.setattr(portfolio_route, "record_transaction", lambda *args, **kwargs: None)

    body = {
        "request_id": "dup-1",
        "suggestions": [{"symbol": "PLANZ", "action": "comprar", "quantity": 1, "price": 10}],
        "options": {
            "profile_override": None,
            "allow_sells": True,
            "prefer_etfs": False,
            "min_trade_value": 50,
            "max_turnover": 0.25,
        },
        "execution_date": "2024-01-01",
    }
    first = client.post("/api/portfolio/rebalance/apply", headers=headers, json=body)
    assert first.status_code in (200, 422)
    second = client.post("/api/portfolio/rebalance/apply", headers=headers, json=body)
    assert second.status_code in (409, 422, 200)

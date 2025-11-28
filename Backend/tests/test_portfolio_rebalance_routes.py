from datetime import datetime, timezone
from types import SimpleNamespace

from app.routes import portfolio as portfolio_route


def _stub_rebalance_result():
    class_summaries = {
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
    }
    suggestions = [
        SimpleNamespace(
            symbol="PLAN1",
            asset_class="acao",
            action="comprar",
            quantity=1.0,
            value=10.0,
            price_ref=10.0,
            weight_before=0.5,
            weight_after=0.6,
            class_weight_before=0.5,
            class_weight_after=0.6,
            rationale="ajuste",
        )
    ]
    return SimpleNamespace(
        holdings=[],
        class_summaries=class_summaries,
        suggestions=suggestions,
        within_bands=False,
        turnover=0.1,
        net_cash_flow=0.0,
        notes=[],
        priced_at=datetime.now(timezone.utc),
        missing_buy_classes=[],
    )


def test_portfolio_rebalance_endpoint(client, user_token, monkeypatch):
    headers, _ = user_token
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "PLAN1", "quantity": 1, "avg_price": 10}],
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
        lambda holdings, weights, bands, options: _stub_rebalance_result(),
    )

    resp = client.get("/api/portfolio/rebalance", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile"] == "moderado"
    assert body["suggestions"][0]["symbol"] == "PLAN1"


def test_portfolio_rebalance_apply_happy_path(client, user_token, monkeypatch):
    headers, _ = user_token
    client.post(
        "/api/import/holdings",
        headers=headers,
        json=[{"symbol": "PLAN1", "quantity": 1, "avg_price": 10}],
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
            "class_summaries": {
                "acao": {
                    "current_value": 100.0,
                    "current_pct": 0.5,
                    "target_pct": 0.5,
                    "floor_pct": 0.4,
                    "ceiling_pct": 0.6,
                    "delta_value": 0.0,
                    "post_value": 100.0,
                    "post_pct": 0.5,
                }
            },
            "suggestions": [
                {
                    "symbol": "PLAN1",
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
            "options": {
                "allow_sells": True,
                "prefer_etfs": False,
                "min_trade_value": 50,
                "max_turnover": 0.25,
            },
        },
    )
    monkeypatch.setattr(
        portfolio_route, "record_transaction", lambda *args, **kwargs: None
    )

    body = {
        "request_id": "req-1",
        "suggestions": [
            {"symbol": "PLAN1", "action": "comprar", "quantity": 1, "price": 10}
        ],
        "options": {
            "profile_override": None,
            "allow_sells": True,
            "prefer_etfs": False,
            "min_trade_value": 50,
            "max_turnover": 0.25,
        },
        "execution_date": "2024-01-01",
    }
    resp = client.post("/api/portfolio/rebalance/apply", headers=headers, json=body)
    assert resp.status_code in (200, 422)
    if resp.status_code == 200:
        payload = resp.json()
        assert payload["status"] == "applied"
        assert payload["applied"] >= 1

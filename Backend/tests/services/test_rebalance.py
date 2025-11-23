import math

from app.services.rebalance import (
    HoldingSnapshot,
    RebalanceOptions,
    rebalance_portfolio,
)


def _snapshot(
    symbol: str,
    asset_class: str,
    *,
    quantity: float,
    price: float,
    **kwargs,
) -> HoldingSnapshot:
    return HoldingSnapshot(
        symbol=symbol,
        name=symbol,
        asset_class=asset_class,
        quantity=quantity,
        price=price,
        value=quantity * price,
        **kwargs,
    )


def test_rebalance_skips_trades_below_min_trade():
    holdings = [
        _snapshot("AAA", "acao", quantity=12, price=10.0),
        _snapshot("BBB", "etf", quantity=8, price=10.0),
    ]
    targets = {"acao": 0.5, "etf": 0.5}
    bands = {"acao": 0.01, "etf": 0.01}
    options = RebalanceOptions(
        allow_sells=True,
        min_trade_value=100.0,
        max_turnover=1.0,
    )

    result = rebalance_portfolio(holdings, targets, bands, options)

    assert result.suggestions == []
    assert math.isclose(result.class_summaries["acao"].current_value, 120.0)
    assert (
        result.class_summaries["acao"].current_value
        == result.class_summaries["acao"].post_value
    )
    assert any("valor minimo" in note.lower() for note in result.notes)


def test_rebalance_generates_trades_with_rounding():
    holdings = [
        _snapshot("AAA", "acao", quantity=20, price=12.0, supports_fractional=True),
        _snapshot(
            "ETF1",
            "etf",
            quantity=10,
            price=6.0,
            qty_step=10,
            supports_fractional=False,
        ),
    ]
    targets = {"acao": 0.4, "etf": 0.6}
    bands = {"acao": 0.02, "etf": 0.02}
    options = RebalanceOptions(
        allow_sells=True,
        min_trade_value=10.0,
        max_turnover=1.0,
    )

    result = rebalance_portfolio(holdings, targets, bands, options)

    sell = next(s for s in result.suggestions if s.symbol == "AAA")
    buy = next(s for s in result.suggestions if s.symbol == "ETF1")

    assert sell.action == "vender"
    assert buy.action == "comprar"
    assert buy.quantity == 20  # múltiplo configurado
    assert buy.value == 120.0
    assert result.net_cash_flow == 0.0

    etf_summary = result.class_summaries["etf"]
    assert math.isclose(etf_summary.current_value, 60.0)
    assert math.isclose(etf_summary.post_value, 180.0)


def test_rebalance_marks_missing_classes_for_candidates():
    holdings = [
        _snapshot("AAA", "acao", quantity=20, price=10.0),
        _snapshot("BBB", "acao", quantity=10, price=10.0),
    ]
    targets = {"acao": 0.3, "etf": 0.35, "fii": 0.35}
    bands = {"acao": 0.01, "etf": 0.02, "fii": 0.02}
    options = RebalanceOptions(
        allow_sells=True,
        min_trade_value=10.0,
        max_turnover=0.5,
    )

    result = rebalance_portfolio(holdings, targets, bands, options)

    assert "etf" in result.missing_buy_classes
    assert "fii" in result.missing_buy_classes


def test_prefer_etfs_prioritizes_buy_budget():
    holdings = [
        _snapshot("OUT1", "outros", quantity=10, price=10.0),
        _snapshot("ETF1", "etf", quantity=5, price=10.0),
        _snapshot("FII1", "fii", quantity=5, price=10.0),
    ]
    targets = {"etf": 0.4, "fii": 0.4, "outros": 0.2}
    bands = {"etf": 0.02, "fii": 0.02, "outros": 0.02}

    options_prefer = RebalanceOptions(
        allow_sells=True,
        min_trade_value=10.0,
        max_turnover=0.3,
        prefer_etfs=True,
    )
    options_neutral = RebalanceOptions(
        allow_sells=True,
        min_trade_value=10.0,
        max_turnover=0.3,
        prefer_etfs=False,
    )

    result_prefer = rebalance_portfolio(holdings, targets, bands, options_prefer)
    result_neutral = rebalance_portfolio(holdings, targets, bands, options_neutral)

    etf_value_prefer = next(
        s.value for s in result_prefer.suggestions if s.symbol == "ETF1"
    )
    fii_value_prefer = next(
        s.value for s in result_prefer.suggestions if s.symbol == "FII1"
    )
    assert etf_value_prefer > fii_value_prefer

    etf_value_neutral = next(
        s.value for s in result_neutral.suggestions if s.symbol == "ETF1"
    )
    fii_value_neutral = next(
        s.value for s in result_neutral.suggestions if s.symbol == "FII1"
    )
    assert math.isclose(etf_value_neutral, fii_value_neutral, rel_tol=0.05)

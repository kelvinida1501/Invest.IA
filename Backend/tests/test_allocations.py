import pytest

from app.services.allocations import (
    _normalize,
    get_allocation_profile,
    normalize_asset_class,
)


def test_normalize_weights_sums_to_one():
    weights = {"acao": 0.5, "etf": 0.5}
    normalized = _normalize(weights)
    assert normalized["acao"] == pytest.approx(0.5)
    assert sum(normalized.values()) == pytest.approx(1.0)


def test_normalize_weights_rejects_invalid():
    with pytest.raises(ValueError):
        _normalize({"acao": 0.0, "etf": -1.0})


@pytest.mark.parametrize(
    "symbol,raw_class,expected",
    [
        ("BOVA11", "fund", "fii"),  # fund with final 11 falls back to FII
        ("IVVB11", "exchange traded fund", "etf"),
        ("XPML11", "", "fii"),  # empty class but endswith 11
        ("BTC", "crypto", "cripto"),
        ("AAPL", "stock", "acao"),
    ],
)
def test_normalize_asset_class(symbol: str, raw_class: str, expected: str):
    assert normalize_asset_class(symbol, raw_class) == expected


def test_get_allocation_profile_fallbacks_to_moderate():
    profile = get_allocation_profile("perfil-invalido")
    assert profile.profile == "moderado"
    assert set(profile.weights.keys()) == {"etf", "acao", "fii", "cripto"}

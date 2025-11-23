import pytest

from app.services.currency import normalize_currency_code


@pytest.mark.parametrize(
    "raw,symbol,expected",
    [
        ("USD", None, "USD"),
        ("us$", None, "USD"),
        ("R$", None, "BRL"),
        (None, "BTC-USD", "USD"),
        (None, "BOVA11.SA", "BRL"),
        (None, "EUR=X", "BRL"),  # fallback default when unknown and no match
    ],
)
def test_normalize_currency_code(raw, symbol, expected):
    assert normalize_currency_code(raw, symbol) == expected


def test_normalize_currency_code_defaults_to_brl():
    assert normalize_currency_code(None, None) == "BRL"

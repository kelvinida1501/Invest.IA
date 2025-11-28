from datetime import datetime

from app.services import fx


class DummyTicker:
    def __init__(self, price: float):
        self.fast_info = {"last_price": price}

    def history(self, *args, **kwargs):
        raise AssertionError("history should not be called when fast_info exists")


def test_get_fx_rate_uses_fast_info(monkeypatch):
    monkeypatch.setattr(
        fx, "yf", type("yf", (), {"Ticker": lambda symbol: DummyTicker(5.0)})
    )
    rate, ts = fx.get_fx_rate("USD", "BRL")
    assert rate == 5.0
    assert isinstance(ts, datetime)


def test_get_fx_rate_identity(monkeypatch):
    rate, ts = fx.get_fx_rate("BRL", "BRL")
    assert rate == 1.0
    assert isinstance(ts, datetime)


def test_get_fx_rate_cache(monkeypatch):
    calls = {"count": 0}

    class T:
        def __init__(self):
            self.fast_info = {"last_price": 4.0}

        def history(self, *args, **kwargs):
            calls["count"] += 1
            raise AssertionError("history should not run")

    monkeypatch.setattr(fx, "yf", type("yf", (), {"Ticker": lambda symbol: T()}))
    fx._FX_CACHE.clear()

    rate1, _ = fx.get_fx_rate("USD", "BRL")
    rate2, _ = fx.get_fx_rate("USD", "BRL")
    assert rate1 == rate2 == 4.0
    assert calls["count"] == 0

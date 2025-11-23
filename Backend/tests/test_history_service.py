from datetime import date

from app.db.models import Asset, AssetPrice
from app.services import history


class DummyHistory:
    def __init__(self, rows):
        self._rows = rows
        self.empty = len(rows) == 0

    def iterrows(self):
        for d, close in self._rows:
            yield type("Idx", (), {"to_pydatetime": lambda self, dt=d: type("D", (), {"date": lambda self: dt})()})(), {
                "Close": close
            }


class DummyTicker:
    def __init__(self, rows):
        self._rows = rows

    def history(self, *args, **kwargs):
        return DummyHistory(self._rows)


def test_ensure_price_history_inserts_missing_rows(db_session, monkeypatch):
    asset = Asset(symbol="ABC", name="ABC", class_="acao", currency="BRL")
    db_session.add(asset)
    db_session.commit()

    rows = [
        (date(2024, 1, 1), 10.0),
        (date(2024, 1, 2), 11.0),
    ]
    monkeypatch.setattr(history.yf, "Ticker", lambda symbol: DummyTicker(rows))

    history.ensure_price_history(db_session, asset, date(2024, 1, 1), date(2024, 1, 3))
    db_session.commit()

    saved = db_session.query(AssetPrice).order_by(AssetPrice.date.asc()).all()
    assert len(saved) == 2
    assert saved[0].close == 10.0 and saved[1].close == 11.0


def test_ensure_history_for_assets_calls_each_asset(db_session, monkeypatch):
    a1 = Asset(symbol="ONE", name="One", class_="acao", currency="BRL")
    a2 = Asset(symbol="TWO", name="Two", class_="acao", currency="BRL")
    db_session.add_all([a1, a2])
    db_session.commit()

    called = {"count": 0}

    def fake_ensure(db, asset, start, end):
        called["count"] += 1

    monkeypatch.setattr(history, "ensure_price_history", fake_ensure)
    history.ensure_history_for_assets(db_session, [a1, a2], date(2024, 1, 1), date(2024, 1, 2))
    assert called["count"] == 2

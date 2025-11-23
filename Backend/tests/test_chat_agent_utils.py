from types import SimpleNamespace

from app.services import chat_agent
from app.db.models import User, Portfolio, Holding, Asset


def test_format_helpers():
    assert chat_agent._format_currency_brl(1234.5).startswith("R$")
    assert chat_agent._format_percentage(12.3) == "12.30%"


def test_build_portfolio_observation_without_portfolio(db_session):
    user = User(name="User", email="u@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()

    obs = chat_agent._build_portfolio_observation(db_session, user)
    assert obs.data["portfolio"] is None
    assert obs.name == "portfolio_overview"


def test_build_portfolio_observation_with_holdings(db_session, monkeypatch):
    user = User(name="User", email="u2@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    portfolio = Portfolio(user_id=user.id, name="P")
    asset = Asset(symbol="ABC", name="ABC", class_="acao", currency="USD", last_quote_price=10.0)
    holding = Holding(portfolio=portfolio, asset=asset, quantity=1.0, avg_price=5.0)
    db_session.add_all([portfolio, asset, holding])
    db_session.commit()

    # avoid FX calls
    monkeypatch.setattr(chat_agent, "get_fx_rate", lambda a, b: (1.0, None))

    obs = chat_agent._build_portfolio_observation(db_session, user)
    assert "Carteira" in obs.content or obs.data["portfolio"] is not None

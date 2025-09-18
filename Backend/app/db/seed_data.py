from sqlalchemy.orm import Session
from .base import SessionLocal
from .models import User, Portfolio, Asset, Holding, NewsItem


def run_seed():
    db: Session = SessionLocal()
    try:
        # usuário + portfolio
        user = db.query(User).filter_by(email="user@example.com").first()
        if not user:
            user = User(
                name="Kelvin", email="user@example.com", password_hash="hash-demo"
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        portfolio = db.query(Portfolio).filter_by(user_id=user.id).first()
        if not portfolio:
            portfolio = Portfolio(user_id=user.id, name="Principal")
            db.add(portfolio)
            db.commit()
            db.refresh(portfolio)

        # assets
        def get_or_create(symbol, name, class_, currency="BRL"):
            a = db.query(Asset).filter_by(symbol=symbol).first()
            if not a:
                a = Asset(symbol=symbol, name=name, class_=class_, currency=currency)
                db.add(a)
                db.commit()
                db.refresh(a)
            return a

        petr4 = get_or_create("PETR4", "Petrobras PN", "acao")
        vale3 = get_or_create("VALE3", "Vale ON", "acao")

        # holdings
        h1 = (
            db.query(Holding)
            .filter_by(portfolio_id=portfolio.id, asset_id=petr4.id)
            .first()
        )
        if not h1:
            db.add(
                Holding(
                    portfolio_id=portfolio.id,
                    asset_id=petr4.id,
                    quantity=10,
                    avg_price=35.0,
                )
            )
        h2 = (
            db.query(Holding)
            .filter_by(portfolio_id=portfolio.id, asset_id=vale3.id)
            .first()
        )
        if not h2:
            db.add(
                Holding(
                    portfolio_id=portfolio.id,
                    asset_id=vale3.id,
                    quantity=5,
                    avg_price=60.0,
                )
            )

        # news
        n1 = db.query(NewsItem).filter_by(url="https://exemplo.com/1").first()
        if not n1:
            db.add(
                NewsItem(
                    title="Petrobras anuncia resultados",
                    url="https://exemplo.com/1",
                    sentiment="positivo",
                )
            )
        n2 = db.query(NewsItem).filter_by(url="https://exemplo.com/2").first()
        if not n2:
            db.add(
                NewsItem(
                    title="Mercado vê volatilidade",
                    url="https://exemplo.com/2",
                    sentiment="negativo",
                )
            )

        db.commit()
        print("Seed concluído.")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()

import pytest
import sys
import types
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from passlib.hash import bcrypt

# Stub yfinance if not installed (evita falha de import nos testes offline)
if "yfinance" not in sys.modules:
    class _DummyHistory:
        empty = True

    class _DummyTicker:
        def __init__(self, *args, **kwargs):
            self.fast_info = {}
            self.info = {}
            self.news = []

        def history(self, *args, **kwargs):
            return _DummyHistory()

    sys.modules["yfinance"] = types.SimpleNamespace(Ticker=_DummyTicker)

from app.main import app
from app.db.base import Base, get_db
from app.db.models import User
from app.routes.auth import create_access_token


# Usa SQLite em memória para isolar os testes
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine
)


def _override_get_db(db_session):
    def _get_db():
        try:
            yield db_session
        finally:
            pass

    return _get_db


@pytest.fixture
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = _override_get_db(db_session)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def user_token(db_session):
    user = User(
        name="Test User",
        email="user@example.com",
        password_hash=bcrypt.hash("secret"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}, user

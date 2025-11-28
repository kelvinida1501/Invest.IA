from types import SimpleNamespace

from app.services import chat_agent
from app.db.models import User


def test_generate_reply_fallback_without_llm(db_session, monkeypatch):
    user = User(name="Chat", email="chat@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()

    monkeypatch.setattr(
        chat_agent,
        "get_settings",
        lambda: SimpleNamespace(chat=SimpleNamespace(history_window=0)),
    )
    # remove LLM to force fallback
    agent = chat_agent.ChatAgent()
    agent._llm = None  # type: ignore
    agent._prompt = None  # type: ignore

    resp = agent.generate_reply(db=db_session, user=user, message="oi", history=[])
    assert resp.reply
    assert resp.used_fallback is True

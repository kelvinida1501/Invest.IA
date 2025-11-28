from app.routes import chat as chat_route


def test_chat_status_disabled(monkeypatch):
    monkeypatch.setattr(
        chat_route,
        "_settings",
        type("S", (), {"chat": type("C", (), {"enabled": False})()})(),
    )
    status = chat_route.get_chat_status()
    assert status.ready is False
    assert status.reason == "chat_disabled"


def test_chat_status_missing_llm(monkeypatch):
    monkeypatch.setattr(
        chat_route,
        "_settings",
        type("S", (), {"chat": type("C", (), {"enabled": True})()})(),
    )
    dummy_agent = type("A", (), {"_llm": None, "_prompt": object()})()
    monkeypatch.setattr(chat_route, "_agent", dummy_agent)
    status = chat_route.get_chat_status()
    assert status.ready is False
    assert status.reason == "llm_unavailable"

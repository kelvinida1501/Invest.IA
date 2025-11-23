from types import SimpleNamespace

from app.routes import chat as chat_route


def test_chat_session_and_history(client, user_token, monkeypatch):
    headers, _ = user_token

    dummy_resp = SimpleNamespace(
        reply="ok",
        observations=[],
        used_fallback=False,
        error=None,
    )

    def fake_generate_reply(db, user, message, history):
        return dummy_resp

    monkeypatch.setattr(
        chat_route,
        "_settings",
        SimpleNamespace(chat=SimpleNamespace(enabled=True, history_window=5)),
    )
    monkeypatch.setattr(chat_route, "_agent", SimpleNamespace(generate_reply=fake_generate_reply))

    session = client.post("/api/chat/session", headers=headers)
    assert session.status_code == 201
    session_id = session.json()["session_id"]

    post = client.post(
        "/api/chat",
        headers=headers,
        json={"message": "hello", "session_id": session_id},
    )
    assert post.status_code == 200

    history = client.get("/api/chat/history", headers=headers, params={"session_id": session_id})
    assert history.status_code == 200
    messages = history.json()["messages"]
    assert len(messages) >= 2  # user + assistant

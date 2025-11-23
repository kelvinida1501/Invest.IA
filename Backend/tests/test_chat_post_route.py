from types import SimpleNamespace

from app.routes import chat as chat_route


def test_chat_post_returns_agent_reply(client, user_token, monkeypatch):
    headers, user = user_token

    dummy_response = SimpleNamespace(
        reply="ok",
        observations=[],
        used_fallback=False,
        error=None,
    )

    def fake_generate_reply(db, user, message, history):
        return dummy_response

    monkeypatch.setattr(chat_route, "_agent", SimpleNamespace(generate_reply=fake_generate_reply))
    # ensure chat enabled
    monkeypatch.setattr(
        chat_route,
        "_settings",
        SimpleNamespace(chat=SimpleNamespace(enabled=True, history_window=5)),
    )

    resp = client.post("/api/chat", headers=headers, json={"message": "teste"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "ok"
    assert body["used_fallback"] is False

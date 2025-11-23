from app.db.models import User


def test_register_login_and_me_flow(client):
    # register
    resp = client.post(
        "/api/auth/register",
        json={"name": "User", "email": "flow@example.com", "password": "secret"},
    )
    assert resp.status_code == 200

    # duplicate
    resp_dup = client.post(
        "/api/auth/register",
        json={"name": "User", "email": "flow@example.com", "password": "secret"},
    )
    assert resp_dup.status_code == 409

    # login ok
    login = client.post(
        "/api/auth/login",
        json={"email": "flow@example.com", "password": "secret"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    # login wrong password
    bad = client.post(
        "/api/auth/login",
        json={"email": "flow@example.com", "password": "wrong"},
    )
    assert bad.status_code == 401

    # me
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "flow@example.com"


def test_me_fails_with_invalid_user(client, db_session):
    user = User(name="Ghost", email="ghost@example.com", password_hash="x")
    db_session.add(user)
    db_session.commit()
    token = "invalid-token"
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (401, 404)

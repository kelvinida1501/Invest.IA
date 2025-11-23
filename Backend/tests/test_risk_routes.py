from app.services import risk_profile


def test_get_and_set_risk_profile(client, user_token):
    headers, _ = user_token

    # GET questions
    questions = client.get("/api/risk/questions")
    assert questions.status_code == 200
    assert questions.json()["version"] == risk_profile.QUESTIONNAIRE_VERSION

    base_answers = {qid: 3 for qid in risk_profile.get_question_ids()}
    payload = {"answers": base_answers, "restrictions": ["fii"]}
    resp = client.post("/api/risk", headers=headers, json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile"] in ("conservador", "moderado", "arrojado")
    assert body["restrictions"] == ["fii"]

    # GET profile returns persisted data
    saved = client.get("/api/risk", headers=headers)
    assert saved.status_code == 200
    assert saved.json()["profile"] == body["profile"]

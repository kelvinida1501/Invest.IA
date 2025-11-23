import pytest

from app.services import risk_profile


def test_compute_risk_profile_basic_paths():
    answers = {qid: 3 for qid in risk_profile.get_question_ids()}
    result = risk_profile.compute_risk_profile(answers)
    assert result.score > 0
    assert result.base_profile in ("conservador", "moderado", "arrojado")
    assert result.profile == result.base_profile
    assert result.rules_applied == []


def test_compute_risk_profile_applies_safety_rules():
    # Respostas muito conservadoras aplicam regras de clamp
    answers = {qid: 5 for qid in risk_profile.get_question_ids()}
    answers.update(
        {
            "tolerance": 1,
            "reaction": 1,
            "liquidity": 2,
            "emergency": 1,
            "horizon": 1,
        }
    )
    result = risk_profile.compute_risk_profile(answers)
    assert result.profile == "conservador"
    assert "cap_moderado_por_tolerancia" in result.rules_applied
    assert "cap_conservador_por_reserva_horizonte" in result.rules_applied


def test_compute_risk_profile_rejects_missing_answers():
    answers = {qid: 3 for qid in risk_profile.get_question_ids()}
    answers.pop(next(iter(answers)))
    with pytest.raises(risk_profile.InvalidRiskAnswer):
        risk_profile.compute_risk_profile(answers)


def test_serialize_questionnaire_contains_all_questions():
    payload = risk_profile.serialize_questionnaire()
    ids = [q["id"] for q in payload["questions"]]
    assert set(ids) == set(risk_profile.get_question_ids())
    assert payload["version"] == risk_profile.QUESTIONNAIRE_VERSION

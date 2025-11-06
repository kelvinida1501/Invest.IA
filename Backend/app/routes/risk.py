import json
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, conint, validator
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import RiskProfile
from app.routes.auth import get_current_user, User  # type: ignore
from app.services.allocations import get_allocation_profile
from app.services.risk_profile import (
    QUESTIONNAIRE_VERSION,
    SCORE_VERSION,
    InvalidRiskAnswer,
    compute_risk_profile,
    get_question_ids,
    serialize_questionnaire,
)

router = APIRouter(prefix="/risk", tags=["risk"])


class RiskAssessmentRequest(BaseModel):
    answers: Dict[str, conint(ge=1, le=5)]
    restrictions: Optional[List[str]] = []

    @validator("answers")
    def validate_answers(cls, value: Dict[str, int]) -> Dict[str, int]:
        expected = set(get_question_ids())
        provided = set(value.keys())
        missing = expected - provided
        extra = provided - expected
        if missing or extra:
            raise ValueError(
                f"Respostas inválidas. Faltando: {sorted(missing)}. Desconhecidas: {sorted(extra)}"
            )
        coerced = {k: int(v) for k, v in value.items()}
        for key, v in coerced.items():
            if v < 1 or v > 5:
                raise ValueError(f"Resposta fora da escala (1-5) para '{key}'.")
        return coerced

    @validator("restrictions", pre=True, always=True)
    def default_restrictions(cls, value):
        if not value:
            return []
        dedup = []
        seen = set()
        for item in value:
            key = str(item).strip()
            if not key:
                continue
            if key not in seen:
                seen.add(key)
                dedup.append(key)
        return dedup


@router.get("/questions")
def get_questions():
    return serialize_questionnaire()


@router.get("")
def get_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rp = db.query(RiskProfile).filter(RiskProfile.user_id == user.id).first()
    allocation_profile = get_allocation_profile(rp.profile if rp else "moderado")
    payload = {"answers": None, "restrictions": []}
    rules_applied: List[str] = []
    base_profile: Optional[str] = None

    if rp and rp.answers:
        try:
            payload = json.loads(rp.answers)
        except json.JSONDecodeError:
            payload = {"answers": None, "restrictions": []}

        answers = payload.get("answers") or {}
        try:
            computation = compute_risk_profile(answers)
            base_profile = computation.base_profile
        except InvalidRiskAnswer:
            base_profile = None

    if rp and rp.rules:
        try:
            rules_applied = list(json.loads(rp.rules))
        except json.JSONDecodeError:
            rules_applied = []

    return {
        "profile": rp.profile if rp else None,
        "score": rp.score if rp else None,
        "base_profile": base_profile,
        "questionnaire_version": (rp.questionnaire_version if rp else None)
        or QUESTIONNAIRE_VERSION,
        "score_version": (rp.score_version if rp else None) or SCORE_VERSION,
        "answers": payload.get("answers"),
        "restrictions": payload.get("restrictions"),
        "rules_applied": rules_applied,
        "last_updated": rp.last_updated if rp else None,
        "allocation": {
            "profile": allocation_profile.profile,
            "weights": allocation_profile.weights,
            "bands": allocation_profile.bands,
            "description": allocation_profile.description,
        },
    }


@router.post("")
def set_profile(
    body: RiskAssessmentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        computation = compute_risk_profile(body.answers)
    except InvalidRiskAnswer as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    payload = {
        "answers": body.answers,
        "restrictions": body.restrictions or [],
    }

    rp = db.query(RiskProfile).filter(RiskProfile.user_id == user.id).first()
    now = datetime.utcnow()

    if not rp:
        rp = RiskProfile(
            user_id=user.id,
            profile=computation.profile,
            score=computation.score,
            last_updated=now,
            questionnaire_version=QUESTIONNAIRE_VERSION,
            score_version=SCORE_VERSION,
            answers=json.dumps(payload),
            rules=json.dumps(computation.rules_applied),
        )
        db.add(rp)
    else:
        rp.profile = computation.profile
        rp.score = computation.score
        rp.last_updated = now
        rp.questionnaire_version = QUESTIONNAIRE_VERSION
        rp.score_version = SCORE_VERSION
        rp.answers = json.dumps(payload)
        rp.rules = json.dumps(computation.rules_applied)

    db.commit()
    db.refresh(rp)

    allocation_profile = get_allocation_profile(computation.profile)

    return {
        "profile": computation.profile,
        "score": computation.score,
        "base_profile": computation.base_profile,
        "questionnaire_version": QUESTIONNAIRE_VERSION,
        "score_version": SCORE_VERSION,
        "rules_applied": computation.rules_applied,
        "answers": body.answers,
        "restrictions": body.restrictions,
        "last_updated": rp.last_updated,
        "allocation": {
            "profile": allocation_profile.profile,
            "weights": allocation_profile.weights,
            "bands": allocation_profile.bands,
            "description": allocation_profile.description,
        },
    }

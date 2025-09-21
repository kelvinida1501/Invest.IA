from fastapi import APIRouter, Depends
from pydantic import BaseModel, conint
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.base import get_db
from app.db.models import RiskProfile
from app.routes.auth import get_current_user, User  # type: ignore

router = APIRouter(prefix="/risk", tags=["risk"])


class RiskAnswers(BaseModel):
    # cinco perguntas, nota 1..5
    q1: conint(ge=1, le=5)
    q2: conint(ge=1, le=5)
    q3: conint(ge=1, le=5)
    q4: conint(ge=1, le=5)
    q5: conint(ge=1, le=5)


def map_score_to_profile(score: int) -> str:
    if score <= 10:  # 5x2
        return "conservador"
    if score <= 17:
        return "moderado"
    return "arrojado"


@router.get("")
def get_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rp = db.query(RiskProfile).filter(RiskProfile.user_id == user.id).first()
    if not rp:
        return {"profile": None, "score": None}
    return {"profile": rp.profile, "score": rp.score, "last_updated": rp.last_updated}


@router.post("")
def set_profile(
    answers: RiskAnswers,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    score = answers.q1 + answers.q2 + answers.q3 + answers.q4 + answers.q5
    profile = map_score_to_profile(score)

    rp = db.query(RiskProfile).filter(RiskProfile.user_id == user.id).first()
    if not rp:
        rp = RiskProfile(
            user_id=user.id,
            profile=profile,
            score=score,
            last_updated=datetime.utcnow(),
        )
        db.add(rp)
    else:
        rp.profile = profile
        rp.score = score
        rp.last_updated = datetime.utcnow()

    db.commit()
    return {"profile": profile, "score": score}

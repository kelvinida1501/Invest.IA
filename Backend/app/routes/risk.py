from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.base import get_db

from app.db.models import RiskProfile

router = APIRouter(prefix="/risk", tags=["risk"])

DEFAULT_USER_ID = 1


@router.get("/profile")
def get_profile(db: Session = Depends(get_db)):
    rp = db.query(RiskProfile).filter(RiskProfile.user_id == DEFAULT_USER_ID).first()
    return rp or {"profile": None, "score": None}


@router.post("/assess")
def assess(scores: list[int], db: Session = Depends(get_db)):
    # scores: lista de 5–7 respostas (1..5)
    total = sum(int(s) for s in scores)
    if total <= 20:
        profile = "conservador"
    elif total <= 30:
        profile = "moderado"
    else:
        profile = "arrojado"

    rp = db.query(RiskProfile).filter(RiskProfile.user_id == DEFAULT_USER_ID).first()
    if rp:
        rp.profile = profile
        rp.score = total
        rp.last_updated = datetime.utcnow()
    else:
        rp = RiskProfile(user_id=DEFAULT_USER_ID, profile=profile, score=total)
        db.add(rp)
    db.commit()
    db.refresh(rp)
    return rp

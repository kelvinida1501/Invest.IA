from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.base import get_db

from app.db.models import NewsItem

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
def list_news(limit: int = 20, db: Session = Depends(get_db)):
    q = db.query(NewsItem).order_by(NewsItem.published_at.desc()).limit(limit)
    return q.all()

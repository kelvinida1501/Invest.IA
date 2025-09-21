from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.db.base import get_db
from app.db.models import NewsItem

router = APIRouter(prefix="/news", tags=["news"])


@router.get("")
def list_news(db: Session = Depends(get_db)):
    items = db.query(NewsItem).order_by(NewsItem.published_at.desc()).limit(20).all()
    if items:
        return [
            {
                "id": n.id,
                "title": n.title,
                "url": n.url,
                "published_at": n.published_at.isoformat() if n.published_at else None,
                "sentiment": n.sentiment,
            }
            for n in items
        ]

    # fallback (stub) se não houver nada no banco
    now = datetime.utcnow()
    return [
        {
            "id": 1,
            "title": "Ibovespa fecha em alta após dados de inflação",
            "url": "https://example.com/noticia-1",
            "published_at": (now - timedelta(hours=2)).isoformat(),
            "sentiment": "positivo",
        },
        {
            "id": 2,
            "title": "Dólar recua com apetite a risco global",
            "url": "https://example.com/noticia-2",
            "published_at": (now - timedelta(hours=5)).isoformat(),
            "sentiment": "neutro",
        },
    ]

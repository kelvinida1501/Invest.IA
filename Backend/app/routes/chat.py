from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.base import get_db

from app.db.models import ChatSession, ChatMessage

router = APIRouter(prefix="/chat", tags=["chat"])
DEFAULT_USER_ID = 1


@router.post("/sessions")
def new_session(db: Session = Depends(get_db)):
    s = ChatSession(user_id=DEFAULT_USER_ID)
    db.add(s)
    db.commit()
    db.refresh(s)
    return {"session_id": s.id}


@router.post("/{session_id}/messages")
def post_message(session_id: int, content: str, db: Session = Depends(get_db)):
    # salva user msg
    m = ChatMessage(session_id=session_id, role="user", content=content)
    db.add(m)
    db.commit()
    db.refresh(m)
    # resposta mock simples (trocar por LLM depois)
    reply_text = "Em breve conectaremos a IA."
    r = ChatMessage(session_id=session_id, role="assistant", content=reply_text)
    db.add(r)
    db.commit()
    db.refresh(r)
    return {"user_message_id": m.id, "assistant_message_id": r.id, "reply": reply_text}


@router.get("/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        {"role": m.role, "content": m.content, "created_at": m.created_at} for m in msgs
    ]

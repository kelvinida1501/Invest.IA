from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.db.models import ChatMessage, ChatSession
from app.routes.auth import User, get_current_user  # type: ignore
from app.services.chat_agent import ChatAgent, ToolObservation
from app.settings import get_settings

router = APIRouter(prefix="/chat", tags=["chat"])

_agent = ChatAgent()
_settings = get_settings()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[int] = Field(
        default=None, description="Identificador da sessao de chat existente."
    )


class ObservationPayload(BaseModel):
    name: str
    description: str
    content: str
    data: Dict[str, Any] | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: int
    used_fallback: bool
    observations: List[ObservationPayload]
    error: Optional[str] = None


class NewSessionResponse(BaseModel):
    session_id: int


class ChatMessagePayload(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: int
    messages: List[ChatMessagePayload]


def _serialize_observation(obs: ToolObservation) -> ObservationPayload:
    return ObservationPayload(
        name=obs.name, description=obs.description, content=obs.content, data=obs.data
    )


def _load_session(db: Session, user: User, session_id: Optional[int]) -> ChatSession:
    if session_id is None:
        session = ChatSession(user_id=user.id, started_at=datetime.utcnow())
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sessao nao encontrada."
        )
    return session


def _fetch_history(db: Session, session_id: int, limit: int) -> List[ChatMessage]:
    query = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    rows = query.all()
    if limit <= 0 or len(rows) <= limit:
        return rows
    return rows[-limit:]


def _persist_message(
    db: Session, session_id: int, role: str, content: str
) -> ChatMessage:
    msg = ChatMessage(
        session_id=session_id, role=role, content=content, created_at=datetime.utcnow()
    )
    db.add(msg)
    return msg


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _settings.chat.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chat desabilitado no momento.",
        )

    user_message = (body.message or "").strip()
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Mensagem vazia."
        )

    session = _load_session(db, current_user, body.session_id)
    history_rows = _fetch_history(db, session.id, _settings.chat.history_window)

    _persist_message(db, session.id, "user", user_message)
    db.commit()

    agent_response = _agent.generate_reply(
        db=db, user=current_user, message=user_message, history=history_rows
    )

    _persist_message(db, session.id, "assistant", agent_response.reply)
    db.commit()

    observations = [_serialize_observation(obs) for obs in agent_response.observations]

    return ChatResponse(
        reply=agent_response.reply,
        session_id=session.id,
        used_fallback=agent_response.used_fallback,
        observations=observations,
        error=agent_response.error,
    )


@router.post(
    "/session", response_model=NewSessionResponse, status_code=status.HTTP_201_CREATED
)
def create_session(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    session = _load_session(db, current_user, None)
    return NewSessionResponse(session_id=session.id)


@router.get("/history", response_model=ChatHistoryResponse)
def get_history(
    session_id: int = Query(..., ge=1, description="Identificador da sessao de chat."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sessao nao encontrada."
        )

    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    payload = [
        ChatMessagePayload(
            id=row.id, role=row.role, content=row.content, created_at=row.created_at
        )
        for row in rows
    ]
    return ChatHistoryResponse(session_id=session.id, messages=payload)

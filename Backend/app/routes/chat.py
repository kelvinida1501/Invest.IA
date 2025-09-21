from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("")
def chat(body: ChatRequest):
    user_msg = body.message.strip()
    if not user_msg:
        return {"reply": "Mande sua pergunta ;)"}
    # MVP: eco inteligente básico
    if "carteira" in user_msg.lower():
        return {"reply": "Sua carteira está balanceada conforme o último resumo."}
    return {"reply": f"Você disse: {user_msg}"}

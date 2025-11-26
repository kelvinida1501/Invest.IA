from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.hash import bcrypt
from pydantic import BaseModel

from app.db.base import get_db
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

# Config simples (em produção usar env vars)
SECRET_KEY = "dev-secret"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    authorization: str = Header(None), db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token inválido")

    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")  # type: ignore[assignment]
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return user


@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    u = User(
        name=body.name.strip(),
        email=email,
        password_hash=bcrypt.hash(body.password),
        created_at=datetime.now(timezone.utc),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"ok": True}


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not bcrypt.verify(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "created_at": current_user.created_at,
    }

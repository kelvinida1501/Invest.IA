from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from passlib.hash import bcrypt
import os
import jwt  # PyJWT
from app.db.base import get_db
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

# === JWT config ===
SECRET_KEY = os.getenv(
    "JWT_SECRET", "dev-secret"
)  # defina JWT_SECRET no .env se quiser
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 dias


def create_access_token(
    *, subject: str, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES
) -> str:
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# === Schemas ===
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# === Helpers de senha ===
def hash_password(pw: str) -> str:
    return bcrypt.hash(pw)


def verify_password(pw: str, hash_: str) -> bool:
    return bcrypt.verify(pw, hash_)


# === Dependência: extrai usuário do token ===
def get_current_user(
    authorization: str = Header(None), db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token inválido")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Token inválido")
        # 'sub' é o id do usuário (string)
        user = db.query(User).filter(User.id == int(sub)).first()
        if not user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")


# === Rotas ===
@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email já cadastrado")

    u = User(
        name=body.name.strip(),
        email=email,
        password_hash=hash_password(body.password),
        created_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    db.refresh(u)

    # opcional: já autenticar após cadastro
    token = create_access_token(subject=str(u.id))
    return {"ok": True, "access_token": token, "token_type": "bearer"}


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = create_access_token(subject=str(user.id))
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "created_at": current_user.created_at,
    }

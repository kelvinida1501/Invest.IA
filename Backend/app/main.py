from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.auth import router as auth_router
from app.routes.assets import router as assets_router
from app.routes.portfolio import router as portfolio_router
from app.routes.news import router as news_router
from app.routes.risk import router as risk_router
from app.routes.chat import router as chat_router

API_PREFIX = "/api"

app = FastAPI(title="Invest.IA API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# registre as rotas COM prefixo
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(assets_router, prefix=API_PREFIX)
app.include_router(portfolio_router, prefix=API_PREFIX)
app.include_router(news_router, prefix=API_PREFIX)
app.include_router(risk_router, prefix=API_PREFIX)
app.include_router(chat_router, prefix=API_PREFIX)


@app.get("/health")
def health():
    return {"ok": True}

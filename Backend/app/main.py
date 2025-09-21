from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.auth import router as auth_router
from app.routes.assets import router as assets_router
from app.routes.portfolio import router as portfolio_router
from app.routes.news import router as news_router
from app.routes.risk import router as risk_router
from app.routes.chat import router as chat_router
from app.routes.holdings import router as holdings_router
from app.routes.prices import router as prices_router
from app.routes.imports import router as imports_router


API_PREFIX = "/api"

app = FastAPI(title="Invest.IA API")

# CORS (origens do Vite em dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registre as rotas COM prefixo /api
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(assets_router, prefix=API_PREFIX)
app.include_router(portfolio_router, prefix=API_PREFIX)
app.include_router(news_router, prefix=API_PREFIX)
app.include_router(risk_router, prefix=API_PREFIX)
app.include_router(chat_router, prefix=API_PREFIX)
app.include_router(holdings_router, prefix=API_PREFIX)
app.include_router(prices_router, prefix=API_PREFIX)
app.include_router(imports_router, prefix=API_PREFIX)


@app.get("/health")
def health():
    return {"ok": True}

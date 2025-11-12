from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable


ALLOCATION_CLASSES = ("acao", "etf", "fii", "cripto")


@dataclass(frozen=True)
class AllocationProfile:
    profile: str
    weights: Dict[str, float]
    bands: Dict[str, float]
    description: str


def _normalize(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(v, 0.0) for v in weights.values())
    if total <= 0:
        raise ValueError("Pesos inválidos para alocação alvo.")
    return {k: max(v, 0.0) / total for k, v in weights.items()}


ALLOCATION_PROFILES: Dict[str, AllocationProfile] = {
    "conservador": AllocationProfile(
        profile="conservador",
        weights=_normalize(
            {
                "etf": 0.60,
                "acao": 0.25,
                "fii": 0.12,
                "cripto": 0.03,
            }
        ),
        bands={
            "etf": 0.03,
            "acao": 0.03,
            "fii": 0.03,
            "cripto": 0.02,
        },
        description="Foco em ETFs amplos e FIIs estáveis, com pequena exposição a cripto.",
    ),
    "moderado": AllocationProfile(
        profile="moderado",
        weights=_normalize(
            {
                "etf": 0.45,
                "acao": 0.35,
                "fii": 0.15,
                "cripto": 0.05,
            }
        ),
        bands={
            "etf": 0.05,
            "acao": 0.05,
            "fii": 0.05,
            "cripto": 0.03,
        },
        description="Equilíbrio entre ETFs globais e ações locais, mantendo FIIs e cripto controlados.",
    ),
    "arrojado": AllocationProfile(
        profile="arrojado",
        weights=_normalize(
            {
                "etf": 0.30,
                "acao": 0.45,
                "fii": 0.15,
                "cripto": 0.10,
            }
        ),
        bands={
            "etf": 0.08,
            "acao": 0.08,
            "fii": 0.06,
            "cripto": 0.05,
        },
        description="Maior exposição a ações e cripto, mantendo FIIs como amortecedor.",
    ),
}


CLASS_LABELS = {
    "acao": "Ações",
    "etf": "ETFs",
    "fii": "FIIs",
    "cripto": "Cripto",
}


def get_allocation_profile(profile: str) -> AllocationProfile:
    key = (profile or "moderado").lower()
    return ALLOCATION_PROFILES.get(key, ALLOCATION_PROFILES["moderado"])


def list_allocation_profiles() -> Iterable[AllocationProfile]:
    return ALLOCATION_PROFILES.values()


def normalize_asset_class(symbol: str, raw_class: str | None) -> str:
    raw = (raw_class or "").strip().lower()
    if raw in ("acao", "stock", "equity", "ações", "bdr"):
        return "acao"
    if raw in ("etf", "exchange traded fund", "fund etf"):
        return "etf"
    if raw in ("fii", "fundo imobiliario", "fundo imobiliário", "fundo", "reit"):
        return "fii"
    if raw in ("fund",):
        symbol_upper = (symbol or "").upper()
        if symbol_upper.endswith("11"):
            return "fii"
        return "etf"
    if raw in ("cripto", "crypto", "cryptocurrency"):
        return "cripto"

    symbol_upper = (symbol or "").upper()
    if symbol_upper.endswith("11"):
        return "fii"
    if symbol_upper.endswith("F11"):
        return "fii"
    if symbol_upper.endswith("34") or symbol_upper.endswith(".SA"):
        # ETFs B3 e BDRs geralmente ficam em ETF/ação
        if symbol_upper.startswith("ETF") or symbol_upper.endswith("11"):
            return "etf"
    if symbol_upper.endswith("-USD") or symbol_upper.endswith("-USDT"):
        return "cripto"
    return "acao"

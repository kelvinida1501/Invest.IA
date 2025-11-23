from __future__ import annotations

from typing import Optional

ALIASES = {
    "US$": "USD",
    "USD$": "USD",
    "$": "USD",
    "R$": "BRL",
    "BR$": "BRL",
}


def normalize_currency_code(
    raw: Optional[str],
    symbol: Optional[str] = None,
    *,
    default: str = "BRL",
) -> str:
    """
    Normalize diferentes representações de moedas para códigos ISO-4217.
    Se não conseguir determinar, retorna o default (BRL).
    """
    if raw:
        cleaned = raw.strip().upper()
        cleaned = cleaned.replace(" ", "")
        cleaned = ALIASES.get(cleaned, cleaned)
        if len(cleaned) == 3 and cleaned.isalpha():
            return cleaned

    if symbol:
        sym = symbol.strip().upper()
        if sym.endswith("-USD") or sym.endswith("=USD") or sym.endswith("/USD"):
            return "USD"
        if sym.endswith("-EUR") or sym.endswith("=EUR") or sym.endswith("/EUR"):
            return "EUR"
        if sym.endswith("-BTC") or sym.endswith("BTC"):
            return "BTC"
        if sym.endswith(".SA") or sym.endswith("-BRL"):
            return "BRL"
        if sym.endswith("-CAD"):
            return "CAD"
        if sym.endswith("-GBP"):
            return "GBP"

    return default.upper()

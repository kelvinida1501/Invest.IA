import hashlib
import logging
import math
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Sequence, Set

import yfinance as yf

logger = logging.getLogger(__name__)

# In-memory cache to avoid rate limiting on frequent calls
_CACHE_LOCK = threading.RLock()
_CACHE_TTL = timedelta(minutes=30)
_CacheEntry = tuple[datetime, list[dict]]
_CACHE: Dict[str, _CacheEntry] = {}

# Basic lexicon for quick rule-based sentiment detection (pt/en blended)
POSITIVE_WORDS = {
    "alta",
    "ganho",
    "otimista",
    "positivo",
    "subida",
    "recorde",
    "avanca",
    "forte",
    "melhora",
    "acima",
    "cresce",
    "surge",
    "bull",
    "rally",
    "valorizacao",
    "expande",
    "supera",
    "progresso",
    "sucesso",
    "lucro",
    "profit",
    "up",
    "beat",
}
NEGATIVE_WORDS = {
    "queda",
    "cai",
    "despenca",
    "negativo",
    "perda",
    "risco",
    "alerta",
    "crise",
    "abaixo",
    "derrota",
    "fraqueza",
    "baixa",
    "pressao",
    "volatil",
    "recuo",
}

SOURCE_CONFIDENCE = {
    "reuters": 1.0,
    "bloomberg": 0.95,
    "valor": 0.9,
    "exame": 0.8,
    "infomoney": 0.85,
    "cnn": 0.75,
    "cnbc": 0.85,
    "investing.com": 0.75,
}

WORD_RE = re.compile(r"[a-zA-Z]+")

ADR_FALLBACKS: Dict[str, List[str]] = {
    "PETR4.SA": ["PETR4", "PBR"],
    "PETR3.SA": ["PETR3", "PBR"],
    "VALE3.SA": ["VALE3", "VALE"],
    "ITUB4.SA": ["ITUB4", "ITUB"],
    "ITUB3.SA": ["ITUB3", "ITUB"],
    "ABEV3.SA": ["ABEV3", "ABEV"],
    "BBDC4.SA": ["BBDC4", "BBD"],
    "BBDC3.SA": ["BBDC3", "BBD"],
    "BBAS3.SA": ["BBAS3", "BBD"],
}


@dataclass(slots=True)
class NormalizedNews:
    url: str
    headline: str
    summary: Optional[str]
    source: Optional[str]
    published_at: Optional[datetime]
    image_url: Optional[str]
    related_tickers: set[str]
    matched_symbols: set[str]


def _cache_key(symbol: str) -> str:
    return symbol.upper().strip()


def _fetch_from_cache(symbol: str) -> Optional[list[dict]]:
    key = _cache_key(symbol)
    now = datetime.now(timezone.utc)
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry:
            expires_at, data = entry
            if expires_at > now:
                return data
            _CACHE.pop(key, None)
    return None


def _store_in_cache(symbol: str, payload: list[dict]) -> None:
    if not payload:
        return
    key = _cache_key(symbol)
    expires_at = datetime.now(timezone.utc) + _CACHE_TTL
    with _CACHE_LOCK:
        _CACHE[key] = (expires_at, payload)


def _safe_fetch_symbol_news(symbol: str) -> list[dict]:
    cached = _fetch_from_cache(symbol)
    if cached is not None:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        payload = ticker.news or []
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Falha ao buscar noticias para %s: %s", symbol, exc)
        payload = []

    if payload:
        _store_in_cache(symbol, payload)
    return payload


def _extract_datetime(raw_ts: Optional[int | float]) -> Optional[datetime]:
    if raw_ts is None:
        return None
    try:
        ts = float(raw_ts)
    except (TypeError, ValueError):
        return None
    # Detect epoch in milliseconds
    if ts > 1e11:
        ts = ts / 1000.0
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (OSError, OverflowError, ValueError):
        return None


def _parse_iso_dt(value: Optional[str]) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        # Try without timezone, assume UTC
        try:
            core = s.split(".")[0]
            return datetime.fromisoformat(core).replace(tzinfo=timezone.utc)
        except Exception:
            return None


def _pick_image(raw: dict) -> Optional[str]:
    thumb = raw.get("thumbnail")
    if not isinstance(thumb, dict):
        return None
    # New payload often has originalUrl
    original = thumb.get("originalUrl")
    if isinstance(original, str) and original:
        return original
    resolutions = thumb.get("resolutions")
    if isinstance(resolutions, list) and resolutions:
        best = max(
            (r for r in resolutions if isinstance(r, dict) and "url" in r),
            key=lambda r: r.get("height", 0),
            default=None,
        )
        if best:
            return best.get("url")
    return thumb.get("url")


def _normalize_single(symbol: str, raw: dict) -> Optional[NormalizedNews]:
    # Support legacy flat shape and new nested "content" shape from Yahoo
    node = raw.get("content") if isinstance(raw.get("content"), dict) else raw

    # URL: link | content.canonicalUrl.url | content.clickThroughUrl.url
    url = (
        raw.get("link")
        or (
            isinstance(node.get("canonicalUrl"), dict)
            and node["canonicalUrl"].get("url")
        )
        or (
            isinstance(node.get("clickThroughUrl"), dict)
            and node["clickThroughUrl"].get("url")
        )
    )

    # Title and summary
    title = raw.get("title") or node.get("title")
    summary = raw.get("summary") or node.get("summary") or node.get("description")

    # Publisher / source
    provider = node.get("provider") if isinstance(node.get("provider"), dict) else None
    source = raw.get("publisher") or (provider and provider.get("displayName"))

    # Published datetime with multiple fallbacks
    published_at = (
        _extract_datetime(raw.get("providerPublishTime"))
        or _extract_datetime(raw.get("timePublished"))
        or _parse_iso_dt(
            node.get("pubDate")
            or node.get("displayTime")
            or node.get("publishedAt")
            or node.get("publishTime")
        )
    )

    # Image
    image = _pick_image(node) or (
        _pick_image(raw) if isinstance(raw.get("thumbnail"), dict) else None
    )

    # Related tickers
    related = set()
    for field in ("tickers", "relatedTickers", "tickerSymbols"):
        values = raw.get(field) or node.get(field)
        if isinstance(values, list):
            related.update(str(v).upper() for v in values)
    if not related:
        related.add(symbol.upper())

    if not url or not title:
        return None

    return NormalizedNews(
        url=url,
        headline=title,
        summary=summary,
        source=source,
        published_at=published_at,
        image_url=image,
        related_tickers=related,
        matched_symbols={symbol.upper()},
    )


def _merge_news(existing: NormalizedNews, incoming: NormalizedNews) -> NormalizedNews:
    existing.related_tickers.update(incoming.related_tickers)
    existing.matched_symbols.update(incoming.matched_symbols)
    if not existing.summary and incoming.summary:
        existing.summary = incoming.summary
    if not existing.image_url and incoming.image_url:
        existing.image_url = incoming.image_url
    if incoming.published_at and (
        not existing.published_at or incoming.published_at > existing.published_at
    ):
        existing.published_at = incoming.published_at
    if not existing.source and incoming.source:
        existing.source = incoming.source
    return existing


def _analyse_sentiment(title: str, summary: Optional[str]) -> tuple[str, float, float]:
    text = f"{title or ''} {summary or ''}".lower()
    tokens = WORD_RE.findall(text)
    if not tokens:
        return "neutro", 0.5, 0.0

    positives = sum(1 for token in tokens if token in POSITIVE_WORDS)
    negatives = sum(1 for token in tokens if token in NEGATIVE_WORDS)
    hits = positives + negatives
    if hits == 0:
        return "neutro", 0.5, 0.0

    raw = (positives - negatives) / hits
    normalized = max(0.0, min(1.0, (raw + 1.0) / 2.0))
    if normalized > 0.65:
        label = "positivo"
    elif normalized < 0.35:
        label = "negativo"
    else:
        label = "neutro"
    magnitude = abs(normalized - 0.5) * 2.0
    return label, round(normalized, 3), round(magnitude, 3)


def _source_confidence(source: Optional[str]) -> float:
    if not source:
        return 0.55
    return SOURCE_CONFIDENCE.get(source.lower(), 0.6)


def _recency_weight(published_at: Optional[datetime]) -> float:
    if not published_at:
        return 0.4
    now = datetime.now(timezone.utc)
    delta_hours = max(0.0, (now - published_at).total_seconds() / 3600.0)
    tau = 48.0
    return math.exp(-delta_hours / tau)


def _build_id(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return digest[:16]


def _symbol_variants(symbol: str) -> List[str]:
    sym = symbol.upper()
    variants: List[str] = [sym]
    if sym.endswith(".SA"):
        base = sym[:-3]
        variants.append(base)
    variants.extend(ADR_FALLBACKS.get(sym, []))
    return list(dict.fromkeys(v for v in variants if v))


def fetch_news_for_symbols(
    symbols: Sequence[str],
    *,
    lookback: timedelta,
    total_limit: int,
    per_symbol_limit: int,
    order_by: str = "recent",
    include_debug: bool = False,
) -> dict:
    max_lookback = min(lookback, timedelta(days=7))
    if not symbols:
        return {
            "symbols": [],
            "items": [],
            "meta": {
                "fetched": 0,
                "limit": total_limit,
                "per_symbol_limit": per_symbol_limit,
                "lookback_hours": int(max_lookback.total_seconds() // 3600),
                "order": order_by,
                "debug": {"reason": "no_symbols"} if include_debug else None,
            },
        }

    symbols_upper = [s.upper() for s in symbols]
    symbols_set: Set[str] = set(symbols_upper)
    aggregated: Dict[str, NormalizedNews] = {}
    stats_raw: Dict[str, int] = {}
    stats_after_cutoff: Dict[str, int] = {}

    for sym in symbols_upper:
        total_raw = 0
        for variant in _symbol_variants(sym):
            raw_items = _safe_fetch_symbol_news(variant)
            total_raw += len(raw_items)
            for payload in raw_items:
                normalized = _normalize_single(sym, payload)
                if not normalized:
                    continue
                key = normalized.url
                if key in aggregated:
                    aggregated[key] = _merge_news(aggregated[key], normalized)
                else:
                    aggregated[key] = normalized
        stats_raw[sym] = total_raw

    cutoff = datetime.now(timezone.utc) - max_lookback
    rows: List[dict] = []
    for item in aggregated.values():
        primary_matches = item.matched_symbols & symbols_set
        if not primary_matches:
            normalized_related = {tick.upper() for tick in item.related_tickers}
            fallback_matches = set()
            for sym in symbols_set:
                base = sym[:-3] if sym.endswith(".SA") else sym
                candidates = {sym, base, f"{base}.SA"}
                if candidates & normalized_related:
                    fallback_matches.add(sym)
            if fallback_matches:
                primary_matches = fallback_matches
                item.matched_symbols.update(primary_matches)
            else:
                if symbols_upper:
                    primary_matches = {symbols_upper[0]}
                    item.matched_symbols.update(primary_matches)
                else:
                    continue
        if item.published_at and item.published_at < cutoff:
            continue
        label, score, magnitude = _analyse_sentiment(item.headline, item.summary)
        recency = _recency_weight(item.published_at)
        confidence = _source_confidence(item.source)
        ranking = round((recency * 0.5) + (magnitude * 0.3) + (confidence * 0.2), 4)
        published_ts = item.published_at.timestamp() if item.published_at else 0.0

        rows.append(
            {
                "id": _build_id(item.url),
                "headline": item.headline,
                "summary": item.summary,
                "url": item.url,
                "source": item.source,
                "published_at": (
                    item.published_at.isoformat() if item.published_at else None
                ),
                "_published_ts": published_ts,
                "image_url": item.image_url,
                "tickers": sorted(item.related_tickers),
                "matched_symbols": sorted(primary_matches),
                "sentiment": {"label": label, "score": score, "magnitude": magnitude},
                "score": ranking,
            }
        )

    for sym in symbols_upper:
        stats_after_cutoff[sym] = sum(
            1 for row in rows if sym in row["matched_symbols"]
        )

    if order_by == "recent":
        rows.sort(key=lambda r: r["_published_ts"], reverse=True)
    else:
        rows.sort(key=lambda r: (r["score"], r["_published_ts"]), reverse=True)

    per_symbol_counts: Dict[str, int] = {sym: 0 for sym in symbols_upper}
    final_items: List[dict] = []

    for data in rows:
        available = next(
            (
                sym
                for sym in data["matched_symbols"]
                if per_symbol_counts.get(sym, 0) < per_symbol_limit
            ),
            None,
        )
        if not available:
            continue
        data["primary_symbol"] = available
        per_symbol_counts[available] = per_symbol_counts.get(available, 0) + 1
        final_items.append(data)
        if len(final_items) >= total_limit:
            break

    for data in final_items:
        data.pop("_published_ts", None)

    earliest_ts = min(
        (row.get("_published_ts") for row in rows if row.get("_published_ts")),
        default=None,
    )
    latest_ts = max(
        (row.get("_published_ts") for row in rows if row.get("_published_ts")),
        default=None,
    )

    meta = {
        "fetched": len(rows),
        "limit": total_limit,
        "per_symbol_limit": per_symbol_limit,
        "lookback_hours": int(max_lookback.total_seconds() // 3600),
        "order": order_by,
    }
    if include_debug:
        reason = None
        if sum(stats_raw.values()) == 0:
            reason = "no_raw_results"
        elif len(rows) == 0:
            reason = "no_news_within_cutoff"
        logger.info(
            "News aggregation: symbols=%s order=%s raw=%s after_cutoff=%s fetched=%s selected=%s",
            symbols_upper,
            order_by,
            stats_raw,
            stats_after_cutoff,
            len(rows),
            len(final_items),
        )
        meta["debug"] = {
            "raw_per_symbol": stats_raw,
            "after_cutoff": stats_after_cutoff,
            "cache_keys": list(_CACHE.keys()),
            "cutoff": cutoff.isoformat(),
            "latest_row": (
                datetime.fromtimestamp(latest_ts, tz=timezone.utc).isoformat()
                if latest_ts
                else None
            ),
            "earliest_row": (
                datetime.fromtimestamp(earliest_ts, tz=timezone.utc).isoformat()
                if earliest_ts
                else None
            ),
            "reason": reason,
        }

    return {
        "symbols": symbols_upper,
        "items": final_items,
        "meta": meta,
    }

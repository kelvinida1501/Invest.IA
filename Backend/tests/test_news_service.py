from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

from app.services import news as news_service


def _ts(hours_ago: int = 0) -> int:
    dt = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return int(dt.timestamp())


def _payload(
    title: str, link: str, publisher: str, tickers: list[str], hours_ago: int = 0
) -> dict:
    return {
        "title": title,
        "link": link,
        "publisher": publisher,
        "providerPublishTime": _ts(hours_ago),
        "relatedTickers": tickers,
    }


def test_fetch_news_for_symbols_deduplicates_and_enriches(monkeypatch):
    samples = {
        "PETR4.SA": [
            _payload(
                "Petrobras registra ganho recorde com alta do petróleo",
                "https://example.com/petr4-positivo",
                "Reuters",
                ["PETR4.SA", "PETR3.SA"],
            )
        ],
        "VALE3.SA": [
            _payload(
                "Petrobras registra ganho recorde com alta do petróleo",
                "https://example.com/petr4-positivo",
                "Reuters",
                ["VALE3.SA", "PETR4.SA"],
            ),
            _payload(
                "Crise global pressiona mineração e indica queda adicional",
                "https://example.com/vale3-negativo",
                "Bloomberg",
                ["VALE3.SA"],
                hours_ago=2,
            ),
        ],
    }

    def fake_fetch(symbol: str) -> list[dict]:
        return [copy.deepcopy(item) for item in samples.get(symbol, [])]

    monkeypatch.setattr(news_service, "_safe_fetch_symbol_news", fake_fetch)

    response = news_service.fetch_news_for_symbols(
        ["PETR4.SA", "VALE3.SA"],
        lookback=timedelta(days=3),
        total_limit=5,
        per_symbol_limit=2,
        order_by="recent",
    )

    assert response["symbols"] == ["PETR4.SA", "VALE3.SA"]
    assert response["meta"]["fetched"] == 2
    assert response["meta"]["order"] == "recent"
    urls = {item["url"]: item for item in response["items"]}
    assert len(urls) == 2, "Should deduplicate news by URL across tickers"

    merged = urls["https://example.com/petr4-positivo"]
    assert set(merged["matched_symbols"]) == {"PETR4.SA", "VALE3.SA"}
    assert merged["sentiment"]["label"] == "positivo"

    negative = urls["https://example.com/vale3-negativo"]
    assert negative["sentiment"]["label"] == "negativo"
    assert negative["primary_symbol"] == "VALE3.SA"


def test_fetch_news_respects_per_symbol_limit(monkeypatch):
    samples = {
        "PETR4.SA": [
            _payload(
                "Alta forte anima investidores",
                "https://example.com/petr4-first",
                "Reuters",
                ["PETR4.SA"],
            ),
            _payload(
                "Pressao adicional limita ganhos",
                "https://example.com/petr4-second",
                "Reuters",
                ["PETR4.SA"],
                hours_ago=1,
            ),
        ],
        "VALE3.SA": [
            _payload(
                "Crise ainda derruba produção",
                "https://example.com/vale3-single",
                "Bloomberg",
                ["VALE3.SA"],
            )
        ],
    }

    def fake_fetch(symbol: str) -> list[dict]:
        return [copy.deepcopy(item) for item in samples.get(symbol, [])]

    monkeypatch.setattr(news_service, "_safe_fetch_symbol_news", fake_fetch)

    response = news_service.fetch_news_for_symbols(
        ["PETR4.SA", "VALE3.SA"],
        lookback=timedelta(days=2),
        total_limit=5,
        per_symbol_limit=1,
        order_by="recent",
    )

    primary_symbols = [item["primary_symbol"] for item in response["items"]]
    assert primary_symbols.count("PETR4.SA") == 1
    assert primary_symbols.count("VALE3.SA") == 1
    assert len(primary_symbols) == 2


def test_fetch_news_matches_related_tickers(monkeypatch):
    samples = {
        "PETR4.SA": [
            {
                "title": "Petrobras testa fallback de ticker",
                "link": "https://example.com/petr4-fallback",
                "publisher": "Reuters",
                "providerPublishTime": _ts(1),
                "relatedTickers": ["PETR4"],
            }
        ]
    }

    def fake_fetch(symbol: str) -> list[dict]:
        return [copy.deepcopy(item) for item in samples.get(symbol, [])]

    monkeypatch.setattr(news_service, "_safe_fetch_symbol_news", fake_fetch)

    response = news_service.fetch_news_for_symbols(
        ["PETR4.SA"],
        lookback=timedelta(days=2),
        total_limit=3,
        per_symbol_limit=2,
        order_by="recent",
        include_debug=True,
    )

    assert response[
        "items"
    ], "Deveria retornar itens mesmo quando apenas related tickers existem"
    item = response["items"][0]
    assert item["primary_symbol"] == "PETR4.SA"
    assert item["matched_symbols"] == ["PETR4.SA"]
    debug = response["meta"]["debug"]
    assert debug["raw_per_symbol"]["PETR4.SA"] == 1
    assert debug["after_cutoff"]["PETR4.SA"] == 1

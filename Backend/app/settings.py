from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import logging

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dotenv is optional in tests
    load_dotenv = None  # type: ignore


_ENV_LOADED = False
logger = logging.getLogger(__name__)


def _load_env_from_files() -> None:
    """Carrega variáveis de ambiente dos arquivos .env conhecidos sem sobrescrever valores já definidos."""
    global _ENV_LOADED
    if _ENV_LOADED or load_dotenv is None:
        return

    settings_path = Path(__file__).resolve()
    repo_root = settings_path.parents[2]
    backend_root = settings_path.parents[1]

    for candidate in (repo_root / ".env", backend_root / ".env"):
        if candidate.is_file():
            load_dotenv(dotenv_path=candidate, override=False)

    _ENV_LOADED = True

    disable_proxies = (os.getenv("LLM_DISABLE_PROXIES", "true") or "true").strip().lower()
    if disable_proxies not in {"0", "false", "no"}:
        removed: list[str] = []
        for key in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "http_proxy",
            "https_proxy",
            "ALL_PROXY",
            "all_proxy",
        ):
            if key in os.environ:
                os.environ.pop(key, None)
                removed.append(key)
        if removed:
            logger.info(
                "LLM_DISABLE_PROXIES ativo; removendo variaveis de proxy para evitar conflitos com o cliente OpenAI: %s",
                ", ".join(removed),
            )


_load_env_from_files()


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


def _get_int(name: str, default: int) -> int:
    raw = _get_env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    raw = _get_env(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    temperature: float
    max_output_tokens: int
    request_timeout: float
    api_key: str | None
    api_base: str | None


@dataclass(frozen=True)
class ChatSettings:
    enabled: bool
    history_window: int
    summary_threshold: int


@dataclass(frozen=True)
class Settings:
    llm: LLMSettings
    chat: ChatSettings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    provider = (_get_env("LLM_PROVIDER", "openai") or "openai").strip().lower()
    llm = LLMSettings(
        provider=provider,
        model=_get_env("LLM_MODEL", "gpt-4o-mini") or "gpt-4o-mini",
        temperature=_get_float("LLM_TEMPERATURE", 0.2),
        max_output_tokens=_get_int("LLM_MAX_OUTPUT_TOKENS", 600),
        request_timeout=_get_float("LLM_REQUEST_TIMEOUT", 30.0),
        api_key=_get_env("OPENAI_API_KEY"),
        api_base=_get_env("LLM_API_BASE"),
    )

    raw_enabled = (_get_env("CHAT_AGENT_ENABLED") or "true").strip().lower()
    chat = ChatSettings(
        enabled=raw_enabled not in {"0", "false", "no"},
        history_window=_get_int("CHAT_HISTORY_WINDOW", 12),
        summary_threshold=_get_int("CHAT_SUMMARY_THRESHOLD", 40),
    )

    return Settings(llm=llm, chat=chat)

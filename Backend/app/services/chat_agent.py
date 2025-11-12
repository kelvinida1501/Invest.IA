from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy.orm import Session, joinedload

try:  # LangChain is optional at import time (e.g., during unit tests before deps install)
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_openai import ChatOpenAI
    from langchain_core.language_models import BaseChatModel
except Exception:  # pragma: no cover - defensive fallback when package missing
    AIMessage = HumanMessage = SystemMessage = object  # type: ignore
    ChatPromptTemplate = MessagesPlaceholder = object  # type: ignore
    StrOutputParser = object  # type: ignore
    ChatOpenAI = BaseChatModel = None  # type: ignore

from app.db.models import (
    ChatMessage as ChatMessageModel,
    Holding,
    Portfolio,
    RiskProfile,
    User,
)
from app.services import news
from app.services.allocations import CLASS_LABELS, normalize_asset_class
from app.settings import get_settings


logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
Voce e o Invest.IA, assistente financeiro virtual que responde em portugues brasileiro.
Contexto: voce ajuda o usuario a entender sua carteira, perfil de risco, noticias relevantes e proximos passos.
Regras:
- Seja direto e gentil; explique numeros com clareza e evite jargoes desnecessarios.
- Responda de forma objetiva (ate cerca de 8 frases). Use bullets curtas quando fizer sentido.
- Sempre deixe claro que a conversa e informativa e nao constitui recomendacao oficial.
- Utilize os dados do contexto e das ferramentas; cite as fontes resumidamente quando usa-las.
- Se alguma informacao nao estiver disponivel, explique o que falta ou como o usuario pode atualizar os dados.
""".strip()


@dataclass
class ToolObservation:
    """Representa o retorno estruturado de uma coleta de dados usada pelo agente."""

    name: str
    description: str
    content: str
    data: Dict[str, Any]


@dataclass
class ChatAgentResponse:
    reply: str
    observations: List[ToolObservation]
    used_fallback: bool
    error: Optional[str] = None


def _format_currency_brl(value: float) -> str:
    formatted = f"{value:,.2f}"
    return f"R$ {formatted.replace(',', 'X').replace('.', ',').replace('X', '.')}"


def _format_percentage(value: float) -> str:
    return f"{value:.2f}%"


def _load_primary_portfolio(db: Session, user_id: int) -> Optional[Portfolio]:
    return (
        db.query(Portfolio)
        .options(joinedload(Portfolio.holdings).joinedload(Holding.asset))
        .filter(Portfolio.user_id == user_id)
        .order_by(Portfolio.created_at.asc())
        .first()
    )


def _build_portfolio_observation(db: Session, user: User) -> ToolObservation:
    portfolio = _load_primary_portfolio(db, user.id)
    if not portfolio:
        return ToolObservation(
            name="portfolio_overview",
            description="Resumo geral da carteira do usuario.",
            content="Usuario ainda nao possui carteira cadastrada.",
            data={
                "portfolio": None,
                "totals": {
                    "current_value": 0.0,
                    "invested_value": 0.0,
                    "pnl_abs": 0.0,
                    "pnl_pct": 0.0,
                },
            },
        )

    holdings_summary: List[Dict[str, Any]] = []
    totals = {
        "current_value": 0.0,
        "invested_value": 0.0,
    }
    class_totals: Dict[str, float] = {}
    latest_quote_at: Optional[datetime] = None
    symbols: List[str] = []

    for holding in portfolio.holdings:
        asset = holding.asset
        if not asset:
            continue
        price = (
            float(asset.last_quote_price)
            if asset.last_quote_price is not None
            else float(holding.avg_price)
        )
        invested = float(holding.quantity) * float(holding.avg_price)
        current_value = float(holding.quantity) * price
        pnl_abs = current_value - invested
        pnl_pct = (pnl_abs / invested * 100.0) if invested > 0 else 0.0

        totals["current_value"] += current_value
        totals["invested_value"] += invested
        class_key = normalize_asset_class(asset.symbol or "", asset.class_)
        class_totals[class_key] = class_totals.get(class_key, 0.0) + current_value
        if asset.symbol:
            symbols.append(asset.symbol)

        if asset.last_quote_at and (
            latest_quote_at is None or asset.last_quote_at > latest_quote_at
        ):
            latest_quote_at = asset.last_quote_at

        holdings_summary.append(
            {
                "holding_id": holding.id,
                "symbol": asset.symbol,
                "name": asset.name,
                "class": class_key,
                "quantity": float(holding.quantity),
                "avg_price": float(holding.avg_price),
                "last_price": price,
                "current_value": current_value,
                "pnl_abs": pnl_abs,
                "pnl_pct": pnl_pct,
            }
        )

    symbols = list(dict.fromkeys(symbols))

    pnl_abs_total = totals["current_value"] - totals["invested_value"]
    pnl_pct_total = (
        (pnl_abs_total / totals["invested_value"] * 100.0)
        if totals["invested_value"] > 0
        else 0.0
    )

    class_breakdown: List[Dict[str, Any]] = []
    for class_key, amount in class_totals.items():
        share = (
            (amount / totals["current_value"] * 100.0)
            if totals["current_value"] > 0
            else 0.0
        )
        class_breakdown.append(
            {
                "class": class_key,
                "label": CLASS_LABELS.get(class_key, class_key.title()),
                "value": amount,
                "share_pct": share,
            }
        )

    class_breakdown.sort(key=lambda item: item["value"], reverse=True)
    holdings_summary.sort(key=lambda item: item["current_value"], reverse=True)

    lines: List[str] = []
    lines.append(
        f"Carteira '{portfolio.name}': valor atual {_format_currency_brl(totals['current_value'])} "
        f"(resultado acumulado {_format_currency_brl(pnl_abs_total)} | {_format_percentage(pnl_pct_total)})."
    )

    if holdings_summary:
        lines.append("Principais posicoes (top 5 por valor atual):")
        for row in holdings_summary[:5]:
            pnl_label = (
                f"{_format_currency_brl(row['pnl_abs'])} ({_format_percentage(row['pnl_pct'])})"
                if totals["invested_value"] > 0
                else f"{_format_currency_brl(row['current_value'])}"
            )
            lines.append(
                f"- {row['symbol']}: {row['class']} | {_format_currency_brl(row['current_value'])} | {pnl_label}"
            )
    else:
        lines.append("Nenhuma posicao cadastrada ate o momento.")

    if class_breakdown:
        share_text = ", ".join(
            f"{item['label']}: {_format_percentage(item['share_pct'])}"
            for item in class_breakdown[:4]
        )
        lines.append(f"Distribuicao por classe: {share_text}.")

    if latest_quote_at:
        lines.append(
            f"Ultima atualizacao de precos: {latest_quote_at.isoformat()} (UTC)."
        )

    return ToolObservation(
        name="portfolio_overview",
        description="Resumo geral da carteira do usuario.",
        content="\n".join(lines),
        data={
            "portfolio": {
                "id": portfolio.id,
                "name": portfolio.name,
                "updated_at": latest_quote_at.isoformat() if latest_quote_at else None,
                "symbols": symbols,
            },
            "totals": {
                "current_value": totals["current_value"],
                "invested_value": totals["invested_value"],
                "pnl_abs": pnl_abs_total,
                "pnl_pct": pnl_pct_total,
            },
            "holdings": holdings_summary,
            "class_breakdown": class_breakdown,
        },
    )


def _build_risk_profile_observation(db: Session, user: User) -> ToolObservation:
    profile = db.query(RiskProfile).filter(RiskProfile.user_id == user.id).first()
    if not profile:
        return ToolObservation(
            name="risk_profile",
            description="Perfil de risco atribuido ao investidor.",
            content="Nenhum perfil de risco calculado.",
            data={"profile": None},
        )

    details = [
        f"Perfil atual: {profile.profile.upper()} | score {profile.score}.",
        f"Ultima atualizacao: {profile.last_updated.isoformat() if profile.last_updated else 'desconhecida'}.",
    ]
    if profile.rules:
        try:
            parsed_rules = json.loads(profile.rules)
            if isinstance(parsed_rules, list) and parsed_rules:
                details.append("Regras aplicadas: " + ", ".join(parsed_rules))
        except json.JSONDecodeError:
            details.append(f"Regras aplicadas (texto): {profile.rules}")

    return ToolObservation(
        name="risk_profile",
        description="Perfil de risco atribuido ao investidor.",
        content="\n".join(details),
        data={
            "profile": profile.profile,
            "score": profile.score,
            "last_updated": (
                profile.last_updated.isoformat() if profile.last_updated else None
            ),
            "rules": profile.rules,
            "questionnaire_version": profile.questionnaire_version,
            "score_version": profile.score_version,
        },
    )


def _build_news_observation(symbols: Iterable[str]) -> ToolObservation:
    symbols_list = [sym for sym in symbols if sym]
    if not symbols_list:
        return ToolObservation(
            name="market_news",
            description="Noticias recentes relacionadas aos ativos do usuario.",
            content="Nao ha ativos na carteira para buscar noticias.",
            data={"items": []},
        )

    try:
        payload = news.fetch_news_for_symbols(
            symbols_list,
            lookback=timedelta(hours=72),
            total_limit=3,
            per_symbol_limit=1,
            order_by="recent",
        )
    except (
        Exception
    ) as exc:  # pragma: no cover - defensive fallback para ambientes offline
        return ToolObservation(
            name="market_news",
            description="Noticias recentes relacionadas aos ativos do usuario.",
            content="Falha ao consultar noticias recentes.",
            data={"items": [], "error": str(exc)},
        )

    items = payload.get("items", [])[:3]
    if not items:
        return ToolObservation(
            name="market_news",
            description="Noticias recentes relacionadas aos ativos do usuario.",
            content="Nenhuma noticia recente encontrada nas ultimas 72 horas.",
            data={"items": []},
        )

    lines = ["Noticias relevantes das ultimas 72 horas:"]
    for item in items:
        headline = item.get("headline")
        source = item.get("source") or "Fonte nao informada"
        sent = item.get("sentiment", {})
        sentiment_label = sent.get("label") or "desconhecido"
        published = item.get("published_at") or "data nao disponivel"
        tickers = ", ".join(item.get("matched_symbols", []))
        lines.append(
            f"- {headline} ({source}, {published}) | Sentimento: {sentiment_label} | Tickers: {tickers}"
        )

    return ToolObservation(
        name="market_news",
        description="Noticias recentes relacionadas aos ativos do usuario.",
        content="\n".join(lines),
        data={
            "items": items,
            "meta": payload.get("meta"),
            "symbols": payload.get("symbols"),
        },
    )


def _convert_history_to_messages(history: Sequence[Any]) -> List[Any]:
    if AIMessage is object:  # LangChain nao disponivel
        return []

    messages: List[Any] = []
    for item in history:
        role = getattr(item, "role", None)
        content = getattr(item, "content", "")
        if isinstance(item, dict):
            role = item.get("role", role)
            content = item.get("content", content)
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
        elif role == "system":
            messages.append(SystemMessage(content=content))
    return messages


class ChatAgent:
    def __init__(self, llm: Optional[BaseChatModel] = None) -> None:
        self._settings = get_settings()
        try:
            self._llm = llm or self._create_default_llm()
        except Exception as exc:
            # Fail-safe: keep server up and use fallback if LLM init fails
            logger.exception("Failed to initialize LLM: %s", exc)
            self._llm = None
        self._prompt = None if ChatPromptTemplate is object else self._build_prompt()

    def _create_default_llm(self) -> Optional[BaseChatModel]:
        if ChatOpenAI is None:
            return None
        llm_settings = self._settings.llm
        if llm_settings.provider != "openai":
            return None
        if not llm_settings.api_key:
            return None
        return ChatOpenAI(
            model=llm_settings.model,
            temperature=llm_settings.temperature,
            max_tokens=llm_settings.max_output_tokens,
            timeout=llm_settings.request_timeout,
            api_key=llm_settings.api_key,
            base_url=llm_settings.api_base,
        )

    def _build_prompt(self) -> Optional[Any]:
        if ChatPromptTemplate is object:
            return None
        return ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("system", "Contexto estruturado coletado:\n\n{context}"),
                MessagesPlaceholder("history"),
                ("human", "{input}"),
            ]
        )

    def _compose_context(self, observations: Sequence[ToolObservation]) -> str:
        segments = []
        for obs in observations:
            segments.append(f"[{obs.name}] {obs.description}\n{obs.content}")
        return "\n\n".join(segments)

    def generate_reply(
        self,
        db: Session,
        user: User,
        message: str,
        history: Sequence[ChatMessageModel] | Sequence[Dict[str, Any]] | None = None,
    ) -> ChatAgentResponse:
        if not message.strip():
            return ChatAgentResponse(
                reply="Poderia reformular sua pergunta? Preciso de uma mensagem com conteudo.",
                observations=[],
                used_fallback=True,
            )

        portfolio_obs = _build_portfolio_observation(db, user)
        observations: List[ToolObservation] = [
            portfolio_obs,
            _build_risk_profile_observation(db, user),
        ]
        portfolio_data = portfolio_obs.data.get("portfolio")
        symbols = (
            portfolio_data.get("symbols", [])
            if isinstance(portfolio_data, dict)
            else []
        )
        news_obs = _build_news_observation(symbols)
        observations.append(news_obs)

        history_messages = _convert_history_to_messages(history or [])
        context = self._compose_context(observations)

        if (
            not self._llm
            or not self._prompt
            or AIMessage is object
            or StrOutputParser is object
        ):
            reply = self._fallback_reply(message, observations)
            return ChatAgentResponse(
                reply=reply, observations=observations, used_fallback=True
            )

        chain = self._prompt | self._llm | StrOutputParser()
        try:
            response_text = chain.invoke(
                {"context": context, "history": history_messages, "input": message}
            )
            reply_text = response_text.strip()
        except Exception as exc:  # pragma: no cover - fallback se modelo falhar
            reply_text = self._fallback_reply(message, observations)
            return ChatAgentResponse(
                reply=reply_text,
                observations=observations,
                used_fallback=True,
                error=str(exc),
            )

        return ChatAgentResponse(
            reply=reply_text,
            observations=observations,
            used_fallback=False,
        )

    def _fallback_reply(
        self, message: str, observations: Sequence[ToolObservation]
    ) -> str:
        lines: List[str] = [
            (
                "Ainda nao consegui consultar o modelo de linguagem, mas aqui vai um resumo "
                "rapido com base nos dados locais:"
            ),
        ]

        portfolio_obs = next(
            (obs for obs in observations if obs.name == "portfolio_overview"), None
        )
        if portfolio_obs and isinstance(portfolio_obs.data, dict):
            totals = portfolio_obs.data.get("totals") or {}
            current_value = totals.get("current_value")
            pnl_abs = totals.get("pnl_abs")
            pnl_pct = totals.get("pnl_pct")
            resumo = []
            if isinstance(current_value, (int, float)):
                resumo.append(
                    f"valor atual {_format_currency_brl(float(current_value))}"
                )
            if isinstance(pnl_abs, (int, float)):
                delta = _format_currency_brl(float(pnl_abs))
                if isinstance(pnl_pct, (int, float)):
                    resumo.append(
                        f"resultado {delta} ({_format_percentage(float(pnl_pct))})"
                    )
                else:
                    resumo.append(f"resultado {delta}")
            if resumo:
                lines.append(f"- Carteira: {' | '.join(resumo)}.")

            holdings = portfolio_obs.data.get("holdings") or []
            if isinstance(holdings, list) and holdings:
                top_holdings = holdings[:3]
                linhas_holdings = []
                for item in top_holdings:
                    symbol = item.get("symbol") or item.get("name") or "Posicao"
                    value = item.get("current_value")
                    pnl = item.get("pnl_pct")
                    partes = []
                    if isinstance(value, (int, float)):
                        partes.append(_format_currency_brl(float(value)))
                    if isinstance(pnl, (int, float)):
                        partes.append(_format_percentage(float(pnl)))
                    resumo_item = " | ".join(partes) if partes else "sem dados"
                    linhas_holdings.append(f"  - {symbol}: {resumo_item}")
                if linhas_holdings:
                    lines.append("- Principais posicoes:")
                    lines.extend(linhas_holdings)

            classes = portfolio_obs.data.get("class_breakdown") or []
            if isinstance(classes, list) and classes:
                top_classes = classes[:3]
                resumo_classes: List[str] = []
                for item in top_classes:
                    share = item.get("share_pct")
                    if not isinstance(share, (int, float)):
                        continue
                    label = item.get("label", item.get("class", "Classe"))
                    resumo_classes.append(
                        f"  - {label}: {_format_percentage(float(share))}"
                    )
                if resumo_classes:
                    lines.append("- Distribuicao por classe:")
                    lines.extend(resumo_classes)

        risk_obs = next(
            (obs for obs in observations if obs.name == "risk_profile"), None
        )
        if risk_obs and isinstance(risk_obs.data, dict):
            profile = risk_obs.data.get("profile")
            score = risk_obs.data.get("score")
            if profile:
                trecho = f"perfil {profile}"
                if isinstance(score, (int, float)):
                    trecho += f" (score {score})"
                lines.append(f"- Perfil de risco: {trecho}.")

        news_obs = next(
            (obs for obs in observations if obs.name == "market_news"), None
        )
        if news_obs and isinstance(news_obs.data, dict):
            itens = news_obs.data.get("items") or []
            if isinstance(itens, list) and itens:
                lines.append("- Noticias recentes:")
                for item in itens[:2]:
                    headline = item.get("headline") or "Noticia"
                    source = item.get("source") or "fonte desconhecida"
                    lines.append(f"  - {headline} ({source})")

        lines.append(
            "Quando o assistente de IA estiver ativo, trarei uma analise personalizada sobre a sua pergunta."
        )

        reply = "\n".join(lines)
        max_len = 900
        if len(reply) > max_len:
            reply = reply[:max_len].rsplit("\n", 1)[0] + "\n..."
        return reply

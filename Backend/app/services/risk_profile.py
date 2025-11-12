from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple


QUESTIONNAIRE_VERSION = "2025-10-31"
SCORE_VERSION = "2025-10-31"


@dataclass(frozen=True)
class Question:
    id: str
    title: str
    group: str
    prompt: str
    weight: int
    scale: Sequence[Tuple[int, str]]


LIKERT_SCALE = (
    (1, "Muito baixo"),
    (2, "Baixo"),
    (3, "Médio"),
    (4, "Alto"),
    (5, "Muito alto"),
)


QUESTIONS: Sequence[Question] = (
    Question(
        id="horizon",
        title="Horizonte de investimento",
        group="Objetivos",
        prompt="Por quanto tempo você pretende manter seus investimentos antes de precisar dos recursos?",
        weight=12,
        scale=(
            (1, "Menos de 2 anos"),
            (2, "Entre 2 e 3 anos"),
            (3, "Entre 3 e 5 anos"),
            (4, "Entre 5 e 10 anos"),
            (5, "Mais de 10 anos"),
        ),
    ),
    Question(
        id="objective",
        title="Objetivo principal",
        group="Objetivos",
        prompt="Qual é o objetivo predominante dos seus investimentos?",
        weight=10,
        scale=(
            (1, "Preservar o capital"),
            (2, "Renda complementar"),
            (3, "Equilíbrio entre renda e crescimento"),
            (4, "Crescimento do patrimônio"),
            (5, "Crescimento agressivo"),
        ),
    ),
    Question(
        id="tolerance",
        title="Tolerância a perdas",
        group="Tolerância a risco",
        prompt="Qual a perda máxima em 12 meses com a qual você se sentiria confortável?",
        weight=18,
        scale=(
            (1, "Até 2%"),
            (2, "Até 5%"),
            (3, "Até 10%"),
            (4, "Até 20%"),
            (5, "Acima de 20%"),
        ),
    ),
    Question(
        id="reaction",
        title="Reação a quedas",
        group="Tolerância a risco",
        prompt="Se sua carteira caísse 15% em um mês, qual seria a sua reação provável?",
        weight=15,
        scale=(
            (1, "Vendaria tudo para evitar novas perdas"),
            (2, "Venderia parte para diminuir risco"),
            (3, "Manteria os investimentos"),
            (4, "Compraria gradualmente"),
            (5, "Compraria mais imediatamente"),
        ),
    ),
    Question(
        id="income",
        title="Estabilidade da renda",
        group="Capacidade financeira",
        prompt="Como você descreveria a estabilidade da sua renda atual?",
        weight=10,
        scale=(
            (1, "Muito instável"),
            (2, "Instável"),
            (3, "Relativamente estável"),
            (4, "Estável"),
            (5, "Muito estável"),
        ),
    ),
    Question(
        id="emergency",
        title="Reserva de emergência",
        group="Capacidade financeira",
        prompt="Sua reserva de emergência cobre quantos meses do seu custo de vida?",
        weight=10,
        scale=(
            (1, "Não possuo"),
            (2, "Menos de 3 meses"),
            (3, "Entre 3 e 6 meses"),
            (4, "Entre 6 e 12 meses"),
            (5, "Mais de 12 meses"),
        ),
    ),
    Question(
        id="liquidity",
        title="Necessidade de liquidez",
        group="Capacidade financeira",
        prompt="Qual o nível de necessidade de resgates rápidos dos investimentos?",
        weight=10,
        scale=(
            (1, "Muito alta"),
            (2, "Alta"),
            (3, "Moderada"),
            (4, "Baixa"),
            (5, "Muito baixa"),
        ),
    ),
    Question(
        id="knowledge",
        title="Conhecimento sobre investimentos",
        group="Experiência",
        prompt="Como você avalia seu conhecimento sobre investimentos?",
        weight=10,
        scale=(
            (1, "Iniciante"),
            (2, "Básico"),
            (3, "Intermediário"),
            (4, "Avançado"),
            (5, "Especialista"),
        ),
    ),
    Question(
        id="volatility",
        title="Conforto com volatilidade",
        group="Tolerância a risco",
        prompt="Quanto de oscilação diária/semana em seus investimentos você tolera?",
        weight=8,
        scale=LIKERT_SCALE,
    ),
    Question(
        id="diversification",
        title="Diversificação desejada",
        group="Experiência",
        prompt="Você prefere concentrar ou diversificar seus investimentos?",
        weight=4,
        scale=(
            (1, "Pouquíssimos ativos"),
            (2, "Poucos ativos"),
            (3, "Diversificação moderada"),
            (4, "Diversificação ampla"),
            (5, "Diversificação muito ampla"),
        ),
    ),
    Question(
        id="international",
        title="Abertura a ativos internacionais e cripto",
        group="Experiência",
        prompt="Qual seu interesse em investir fora do Brasil ou em criptoativos?",
        weight=2,
        scale=(
            (1, "Nenhum interesse"),
            (2, "Baixo interesse"),
            (3, "Moderado"),
            (4, "Alto"),
            (5, "Muito alto"),
        ),
    ),
    Question(
        id="monitoring",
        title="Frequência de acompanhamento",
        group="Comportamento",
        prompt="Com que frequência você acompanha seus investimentos?",
        weight=1,
        scale=(
            (1, "Menos de uma vez por trimestre"),
            (2, "Trimestralmente"),
            (3, "Mensalmente"),
            (4, "Semanalmente"),
            (5, "Diariamente"),
        ),
    ),
)


QUESTION_INDEX = {q.id: q for q in QUESTIONS}
QUESTION_IDS = {q.id for q in QUESTIONS}
TOTAL_WEIGHT = sum(q.weight for q in QUESTIONS)

PROFILE_ORDER = ("conservador", "moderado", "arrojado")


@dataclass
class RiskComputation:
    score: int
    profile: str
    base_profile: str
    rules_applied: List[str]


class InvalidRiskAnswer(Exception):
    """Raised when answers are missing or invalid for the questionnaire version."""


def _normalize_answer(value: int) -> float:
    return (max(1, min(5, value)) - 1) / 4.0


def _score_to_profile(score: int) -> str:
    if score <= 40:
        return "conservador"
    if score <= 70:
        return "moderado"
    return "arrojado"


def _clamp_profile(profile: str, max_profile: str) -> str:
    try:
        current_idx = PROFILE_ORDER.index(profile)
        max_idx = PROFILE_ORDER.index(max_profile)
    except ValueError:
        return profile
    if current_idx > max_idx:
        return PROFILE_ORDER[max_idx]
    return profile


def compute_risk_profile(answers: Dict[str, int]) -> RiskComputation:
    missing = QUESTION_IDS - set(answers.keys())
    extra = set(answers.keys()) - QUESTION_IDS
    if missing or extra:
        raise InvalidRiskAnswer(
            f"Respostas inválidas. Faltando: {sorted(missing)}. Desconhecidas: {sorted(extra)}"
        )

    weighted_sum = 0.0
    for q in QUESTIONS:
        weighted_sum += _normalize_answer(int(answers[q.id])) * q.weight

    score = int(round((weighted_sum / TOTAL_WEIGHT) * 100))
    base_profile = _score_to_profile(score)
    profile = base_profile
    rules_applied: List[str] = []

    # Regras de segurança
    if answers["tolerance"] <= 2:
        if "cap_moderado_por_tolerancia" not in rules_applied:
            rules_applied.append("cap_moderado_por_tolerancia")
        profile = _clamp_profile(profile, "moderado")

    if answers["reaction"] <= 2:
        if "cap_moderado_por_reacao" not in rules_applied:
            rules_applied.append("cap_moderado_por_reacao")
        profile = _clamp_profile(profile, "moderado")

    if answers["liquidity"] <= 2:
        if "cap_moderado_por_liquidez" not in rules_applied:
            rules_applied.append("cap_moderado_por_liquidez")
        profile = _clamp_profile(profile, "moderado")

    if answers["emergency"] <= 2 and answers["horizon"] <= 2:
        if "cap_conservador_por_reserva_horizonte" not in rules_applied:
            rules_applied.append("cap_conservador_por_reserva_horizonte")
        profile = _clamp_profile(profile, "conservador")

    return RiskComputation(
        score=score,
        profile=profile,
        base_profile=base_profile,
        rules_applied=rules_applied,
    )


def serialize_questionnaire() -> Dict[str, object]:
    questions_payload = []
    for q in QUESTIONS:
        questions_payload.append(
            {
                "id": q.id,
                "title": q.title,
                "group": q.group,
                "prompt": q.prompt,
                "weight": q.weight,
                "scale": [{"value": value, "label": label} for value, label in q.scale],
            }
        )

    return {
        "version": QUESTIONNAIRE_VERSION,
        "scale": {"min": 1, "max": 5},
        "questions": questions_payload,
    }


def get_question_ids() -> Sequence[str]:
    return tuple(q.id for q in QUESTIONS)

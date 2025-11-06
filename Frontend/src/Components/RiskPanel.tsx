import React, { useEffect, useMemo, useState } from 'react';
import api from '../Api/ApiClient';

type RiskLevel = 'conservador' | 'moderado' | 'arrojado';

type RiskQuestion = {
  id: string;
  title: string;
  group: string;
  prompt: string;
  weight: number;
  scale: Array<{ value: number; label: string }>;
};

type QuestionnairePayload = {
  version: string;
  scale: { min: number; max: number };
  questions: RiskQuestion[];
};

type AllocationInfo = {
  profile: string;
  weights: Record<string, number>;
  bands: Record<string, number>;
  description: string;
};

type RiskProfileResponse = {
  profile: RiskLevel | string | null;
  score: number | null;
  base_profile?: RiskLevel | string | null;
  questionnaire_version: string;
  score_version: string;
  answers?: Record<string, number>;
  restrictions?: string[];
  rules_applied?: string[];
  last_updated?: string;
  allocation: AllocationInfo;
};

const PROFILE_LABEL: Record<string, string> = {
  conservador: 'Conservador',
  moderado: 'Moderado',
  arrojado: 'Arrojado',
};

const PROFILE_COLOR: Record<string, string> = {
  conservador: '#1e88e5',
  moderado: '#fb8c00',
  arrojado: '#43a047',
};

const CLASS_LABELS: Record<string, string> = {
  acao: 'Ações',
  etf: 'ETFs',
  fii: 'FIIs',
  cripto: 'Cripto',
};

const DEFAULT_SLIDER_VALUE = 3;
const QUESTIONS_PER_STEP = 4;

const BASE_RESTRICTION_OPTIONS = [
  { id: 'excluir_cripto', label: 'Evitar criptoativos' },
  { id: 'excluir_armas', label: 'Evitar setor bélico' },
  { id: 'excluir_tabaco', label: 'Evitar tabaco e jogos' },
  { id: 'foco_esg', label: 'Priorizar empresas com foco ESG' },
];

function buildInitialAnswers(questions: RiskQuestion[], existing?: Record<string, number>) {
  const next: Record<string, number> = {};
  questions.forEach((question) => {
    const value = existing?.[question.id];
    next[question.id] = typeof value === 'number' ? value : DEFAULT_SLIDER_VALUE;
  });
  return next;
}

function formatPercent(value: number | undefined, digits = 1) {
  if (value === undefined || Number.isNaN(value)) {
    return '--';
  }
  return `${(value * 100).toFixed(digits)}%`;
}

function formatCurrency(value: number | undefined) {
  if (value === undefined || Number.isNaN(value)) {
    return '--';
  }
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

export default function RiskPanel() {
  const [questionnaire, setQuestionnaire] = useState<QuestionnairePayload | null>(null);
  const [profile, setProfile] = useState<RiskProfileResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [wizardOpen, setWizardOpen] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [restrictions, setRestrictions] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [questionsResp, profileResp] = await Promise.all([
          api.get('/risk/questions'),
          api.get('/risk'),
        ]);
        const qData: QuestionnairePayload = questionsResp.data;
        setQuestionnaire(qData);

        const pData: RiskProfileResponse = profileResp.data;
        setProfile(pData);

        setAnswers(buildInitialAnswers(qData.questions, pData.answers));
        setRestrictions(pData.restrictions ?? []);
        setActiveStep(0);
      } catch (err: any) {
        const message =
          err?.response?.data?.detail ||
          err?.message ||
          'Não foi possível carregar o questionário de risco.';
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const totalSteps = useMemo(() => {
    if (!questionnaire) return 0;
    return Math.ceil(questionnaire.questions.length / QUESTIONS_PER_STEP);
  }, [questionnaire]);

  const restrictionOptions = useMemo(() => {
    const current = new Map(BASE_RESTRICTION_OPTIONS.map((opt) => [opt.id, opt.label]));
    restrictions.forEach((item) => {
      if (!current.has(item)) {
        current.set(item, item);
      }
    });
    return Array.from(current.entries()).map(([id, label]) => ({ id, label }));
  }, [restrictions]);

  const currentQuestions = useMemo(() => {
    if (!questionnaire) return [];
    const start = activeStep * QUESTIONS_PER_STEP;
    const end = start + QUESTIONS_PER_STEP;
    return questionnaire.questions.slice(start, end);
  }, [questionnaire, activeStep]);

  const openWizard = () => {
    if (questionnaire) {
      setAnswers(buildInitialAnswers(questionnaire.questions, profile?.answers));
      setRestrictions(profile?.restrictions ?? []);
    }
    setActiveStep(0);
    setSaveError(null);
    setWizardOpen(true);
  };

  const handleAnswerChange = (questionId: string, value: number) => {
    setAnswers((prev) => ({
      ...prev,
      [questionId]: value,
    }));
  };

  const toggleRestriction = (id: string) => {
    setRestrictions((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSave = async () => {
    if (!questionnaire) return;
    setSaving(true);
    setSaveError(null);
    try {
      const payload = {
        answers,
        restrictions,
      };
      const { data } = await api.post('/risk', payload);
      const mergedProfile: RiskProfileResponse = {
        ...(profile ?? ({} as RiskProfileResponse)),
        ...data,
      };
      setProfile(mergedProfile);
      setWizardOpen(false);
    } catch (err: any) {
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        'Não foi possível salvar o perfil de risco.';
      setSaveError(message);
    } finally {
      setSaving(false);
    }
  };

  const riskLabel = profile?.profile ? PROFILE_LABEL[profile.profile] ?? profile.profile : null;
  const badgeColor = profile?.profile ? PROFILE_COLOR[profile.profile] ?? '#9e9e9e' : '#9e9e9e';

  return (
    <div className="risk-panel">
      {loading ? (
        <p className="muted">Carregando informações do perfil...</p>
      ) : error ? (
        <div className="error-block">{error}</div>
      ) : (
        <>
          <header
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              gap: 16,
            }}
          >
            <div>
              <div className="muted" style={{ fontSize: 12 }}>
                Perfil atual
              </div>
              <div style={{ fontWeight: 700, color: badgeColor }}>
                {riskLabel ?? 'Não definido'}
                {typeof profile?.score === 'number' && (
                  <span style={{ marginLeft: 8, fontWeight: 500, color: '#ccc' }}>
                    ({profile.score} pts)
                  </span>
                )}
              </div>
              {profile?.base_profile && profile.base_profile !== profile.profile && (
                <div className="muted" style={{ fontSize: 12 }}>
                  Base calculada: {PROFILE_LABEL[profile.base_profile] ?? profile.base_profile}
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: 8, marginLeft: 'auto' }}>
              <button className="btn btn-primary" onClick={openWizard}>
                {profile?.profile ? 'Reavaliar perfil' : 'Definir perfil'}
              </button>
              {wizardOpen && (
                <button className="btn btn-ghost" onClick={() => setWizardOpen(false)}>
                  Fechar
                </button>
              )}
            </div>
          </header>

          {profile?.rules_applied && profile.rules_applied.length > 0 && (
            <div className="rule-badges">
              <div className="muted" style={{ marginBottom: 4 }}>
                Regras de segurança aplicadas
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {profile.rules_applied.map((rule) => (
                  <span
                    key={rule}
                    style={{
                      background: '#263238',
                      color: '#fff',
                      borderRadius: 999,
                      padding: '4px 12px',
                      fontSize: 12,
                    }}
                  >
                    {regraLabel(rule)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {profile?.allocation && (
            <section style={{ marginTop: 16 }}>
              <div className="muted" style={{ marginBottom: 4 }}>
                Alocação alvo ({profile.allocation.profile})
              </div>
              <p style={{ marginTop: 0, fontSize: 13, color: '#bbb' }}>
                {profile.allocation.description}
              </p>
              <div style={{ overflowX: 'auto' }}>
                <table className="table">
                  <thead>
                  <tr>
                    <th>Classe</th>
                    <th>Alvo</th>
                    <th>Banda</th>
                  </tr>
                  </thead>
                  <tbody>
                  {Object.keys(profile.allocation.weights).map((cls) => (
                    <tr key={cls}>
                      <td>{CLASS_LABELS[cls] ?? cls.toUpperCase()}</td>
                      <td>{formatPercent(profile.allocation.weights[cls], 1)}</td>
                      <td>
                        ±
                        {formatPercent(profile.allocation.bands?.[cls] ?? 0, 1)}
                      </td>
                    </tr>
                  ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {profile?.restrictions && profile.restrictions.length > 0 && (
            <section style={{ marginTop: 16 }}>
              <div className="muted" style={{ marginBottom: 4 }}>
                Restrições registradas
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {profile.restrictions.map((item) => (
                  <span
                    key={item}
                    style={{
                      background: '#2e3b43',
                      color: '#fff',
                      borderRadius: 6,
                      padding: '4px 10px',
                      fontSize: 12,
                    }}
                  >
                    {restrictionOptions.find((opt) => opt.id === item)?.label ?? item}
                  </span>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      {wizardOpen && questionnaire && (
        <section
          style={{
            marginTop: 20,
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 12,
            padding: 16,
            background: '#101b22',
          }}
        >
          <header style={{ marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Questionário do investidor</h3>
            <div className="muted" style={{ fontSize: 12 }}>
              Passo {activeStep + 1} de {totalSteps}
            </div>
          </header>

          {saveError && <div className="error-block">{saveError}</div>}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {currentQuestions.map((question) => {
              const value = answers[question.id] ?? DEFAULT_SLIDER_VALUE;
              const scaleLabel =
                question.scale.find((option) => option.value === value)?.label ?? '';

              return (
                <div
                  key={question.id}
                  style={{
                    padding: 12,
                    borderRadius: 10,
                    background: '#14222a',
                    border: '1px solid rgba(255,255,255,0.04)',
                  }}
                >
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontWeight: 600 }}>{question.title}</div>
                    <div className="muted" style={{ fontSize: 13 }}>
                      {question.prompt}
                    </div>
                  </div>

                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'minmax(80px, 1fr) minmax(160px, 2fr) minmax(80px, 1fr)',
                      gap: 12,
                      alignItems: 'center',
                    }}
                  >
                    <span style={{ fontSize: 12, color: '#9fb3c8' }}>
                      {question.scale[0]?.label}
                    </span>
                    <input
                      type="range"
                      min={questionnaire.scale.min}
                      max={questionnaire.scale.max}
                      step={1}
                      value={value}
                      onChange={(event) =>
                        handleAnswerChange(question.id, parseInt(event.target.value, 10))
                      }
                    />
                    <span style={{ fontSize: 12, color: '#9fb3c8', textAlign: 'right' }}>
                      {question.scale[question.scale.length - 1]?.label}
                    </span>
                  </div>

                  <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>
                    Selecionado: <strong>{scaleLabel}</strong>
                  </div>
                </div>
              );
            })}
          </div>

          {activeStep === totalSteps - 1 && (
            <section style={{ marginTop: 20 }}>
              <div className="muted" style={{ marginBottom: 8 }}>
                Preferências e restrições
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
                {restrictionOptions.map((option) => {
                  const checked = restrictions.includes(option.id);
                  return (
                    <label
                      key={option.id}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '6px 10px',
                        borderRadius: 8,
                        background: checked ? '#1b2c35' : '#0e171d',
                        border: `1px solid ${checked ? '#1e88e5' : 'rgba(255,255,255,0.06)'}`,
                        cursor: 'pointer',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleRestriction(option.id)}
                      />
                      <span>{option.label}</span>
                    </label>
                  );
                })}
              </div>
            </section>
          )}

          <footer
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginTop: 20,
              gap: 8,
            }}
          >
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className="btn btn-ghost"
                onClick={() => setWizardOpen(false)}
                disabled={saving}
              >
                Cancelar
              </button>
              <button
                className="btn btn-ghost"
                onClick={() => setActiveStep((prev) => Math.max(prev - 1, 0))}
                disabled={saving || activeStep === 0}
              >
                Voltar
              </button>
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              {activeStep < totalSteps - 1 ? (
                <button
                  className="btn btn-primary"
                  onClick={() => setActiveStep((prev) => Math.min(prev + 1, totalSteps - 1))}
                >
                  Próximo
                </button>
              ) : (
                <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                  {saving ? 'Salvando...' : 'Salvar perfil'}
                </button>
              )}
            </div>
          </footer>
        </section>
      )}
    </div>
  );
}

function regraLabel(rule: string) {
  switch (rule) {
    case 'cap_moderado_por_tolerancia':
      return 'Limite por tolerância a perdas';
    case 'cap_moderado_por_reacao':
      return 'Limite por reação a quedas';
    case 'cap_moderado_por_liquidez':
      return 'Limite por necessidade de liquidez';
    case 'cap_conservador_por_reserva_horizonte':
      return 'Limite por reserva e horizonte curtos';
    default:
      return rule;
  }
}

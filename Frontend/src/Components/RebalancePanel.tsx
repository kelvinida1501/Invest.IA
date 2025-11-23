import React, { useEffect, useMemo, useState } from 'react';
import api from '../Api/ApiClient';

type RiskLevel = 'conservador' | 'moderado' | 'arrojado' | string;

type ClassSummary = {
  label: string;
  current_value: number;
  current_pct: number;
  target_pct: number;
  floor_pct: number;
  ceiling_pct: number;
  delta_value: number;
  post_value: number;
  post_pct: number;
  delta_pct: number;
};

type Suggestion = {
  symbol: string;
  class: string;
  action: string;
  quantity: number;
  value: number;
  price_ref: number;
  weight_before: number;
  weight_after: number;
  class_weight_before: number;
  class_weight_after: number;
  rationale: string;
};

type CandidateSuggestion = {
  symbol: string;
  description?: string;
  class: string;
  class_label?: string;
};

type RebalanceResponse = {
  profile: RiskLevel;
  profile_source: 'default' | 'stored' | 'override' | string;
  score: number | null;
  total_value: number;
  total_value_after: number;
  targets: Record<string, number>;
  bands: Record<string, number>;
  classes: Record<string, ClassSummary>;
  suggestions: Suggestion[];
  within_bands: boolean;
  turnover: number;
  net_cash_flow: number;
  rules_applied: string[];
  notes: string[];
  as_of?: string;
  candidates?: Record<string, CandidateSuggestion[]>;
  options: {
    allow_sells: boolean;
    prefer_etfs: boolean;
    min_trade_value: number;
    max_turnover: number;
  };
};

const PROFILE_LABEL: Record<string, string> = {
  conservador: 'Conservador',
  moderado: 'Moderado',
  arrojado: 'Arrojado',
};

const CLASS_LABELS: Record<string, string> = {
  acao: 'Ações',
  etf: 'ETFs',
  fii: 'FIIs',
  cripto: 'Cripto',
};

function formatPercent(value: number | undefined, digits = 2) {
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

function formatDateTime(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString('pt-BR', {
    dateStyle: 'short',
    timeStyle: 'short',
  });
}

function generateRequestId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `rebalance-${Date.now()}`;
}

function isoTodayLocal() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function RebalancePanel() {
  const [data, setData] = useState<RebalanceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [profileOverride, setProfileOverride] = useState<RiskLevel | ''>('');
  const [allowSells, setAllowSells] = useState(true);
  const [preferEtfs, setPreferEtfs] = useState(false);
  const [minTradeValue, setMinTradeValue] = useState(100);
  const [maxTurnoverPercent, setMaxTurnoverPercent] = useState(25);
  const [applying, setApplying] = useState(false);
  const [applyError, setApplyError] = useState<string | null>(null);
  const [applyMessage, setApplyMessage] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
     setApplyError(null);
     setApplyMessage(null);
    try {
      const params = new URLSearchParams();
      if (profileOverride) {
        params.set('profile_override', String(profileOverride));
      }
      params.set('allow_sells', String(allowSells));
      params.set('prefer_etfs', String(preferEtfs));
      params.set('min_trade_value', String(minTradeValue));
      params.set('max_turnover', String(maxTurnoverPercent / 100));

      const query = params.toString();
      const url = query ? `/portfolio/rebalance?${query}` : '/portfolio/rebalance';
      const { data } = await api.get(url);
      setData(data);
    } catch (err: any) {
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        'Falha ao calcular sugestões de rebalanceamento.';
      setError(message);
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const classEntries = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.classes ?? {}).map(([key, summary]) => ({
      key,
      ...summary,
    }));
  }, [data]);

  const profileLabel = data?.profile ? PROFILE_LABEL[data.profile] ?? data.profile : null;
  const asOfLabel = useMemo(() => formatDateTime(data?.as_of), [data?.as_of]);

  const netCashFlowLabel = useMemo(() => {
    if (!data) return null;
    if (Math.abs(data.net_cash_flow) < 1e-2) {
      return 'Fluxo de caixa neutro';
    }
    if (data.net_cash_flow > 0) {
      return `Aporte sugerido: ${formatCurrency(data.net_cash_flow)}`;
    }
    return `Caixa liberado: ${formatCurrency(Math.abs(data.net_cash_flow))}`;
  }, [data]);

  const handleApply = async () => {
    if (!data || data.suggestions.length === 0 || applying) {
      return;
    }
    setApplying(true);
    setApplyError(null);
    setApplyMessage(null);
    const requestId = generateRequestId();
    const payload = {
      request_id: requestId,
      suggestions: data.suggestions.map((suggestion) => ({
        symbol: suggestion.symbol,
        action: suggestion.action,
        quantity: Math.abs(suggestion.quantity),
        price: suggestion.price_ref,
      })),
      options: {
        profile_override: profileOverride || null,
        allow_sells: allowSells,
        prefer_etfs: preferEtfs,
        min_trade_value: minTradeValue,
        max_turnover: maxTurnoverPercent / 100,
      },
      execution_date: isoTodayLocal(),
    };

    try {
      await api.post('/portfolio/rebalance/apply', payload);
      setApplyMessage('Plano aplicado com sucesso.');
      await load();
    } catch (err: any) {
      const message =
        err?.response?.data?.detail || err?.message || 'Falha ao aplicar plano.';
      setApplyError(message);
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="rebalance-panel">
      <section
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 12,
          alignItems: 'center',
        }}
      >
        <div>
          <div className="muted" style={{ fontSize: 12 }}>
            Perfil considerado
          </div>
          <div style={{ fontWeight: 700 }}>
            {profileLabel ?? 'Não calculado'}
            {data?.profile_source === 'override' && <span style={{ marginLeft: 8 }}>(override)</span>}
          </div>
          {typeof data?.score === 'number' && (
            <div className="muted" style={{ fontSize: 12 }}>
              Score atual: {data.score} pts
            </div>
          )}
          {asOfLabel && (
            <div className="muted" style={{ fontSize: 12 }}>
              Dados atualizados em {asOfLabel}
            </div>
          )}
        </div>

      </section>

      <section
        style={{
          marginTop: 16,
          padding: 16,
          borderRadius: 12,
          border: '1px solid rgba(255,255,255,0.05)',
          background: '#101b22',
          display: 'grid',
          gap: 12,
        }}
      >
        <h3 style={{ margin: 0 }}>Parâmetros</h3>
        <div
          style={{
            display: 'grid',
            gap: 12,
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          }}
        >
          <div>
            <label className="input-label">Forçar perfil</label>
            <select
              className="input"
              value={profileOverride}
              onChange={(event) => setProfileOverride(event.target.value as RiskLevel | '')}
            >
              <option value="">Usar perfil salvo</option>
              <option value="conservador">Conservador</option>
              <option value="moderado">Moderado</option>
              <option value="arrojado">Arrojado</option>
            </select>
          </div>

          <div>
            <label className="input-label">Valor mínimo por ordem (R$)</label>
            <input
              className="input"
              type="number"
              min={0}
              value={minTradeValue}
              onChange={(event) => setMinTradeValue(Number(event.target.value) || 0)}
            />
          </div>

          <div>
            <label className="input-label">Turnover máximo (%)</label>
            <input
              className="input"
              type="number"
              min={0}
              max={100}
              value={maxTurnoverPercent}
              onChange={(event) => setMaxTurnoverPercent(Number(event.target.value) || 0)}
            />
          </div>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              id="allow-sells"
              type="checkbox"
              checked={allowSells}
              onChange={(event) => setAllowSells(event.target.checked)}
            />
            <label htmlFor="allow-sells" className="input-label">
              Permitir vendas
            </label>
          </div>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              id="prefer-etfs"
              type="checkbox"
              checked={preferEtfs}
              onChange={(event) => setPreferEtfs(event.target.checked)}
            />
            <label htmlFor="prefer-etfs" className="input-label">
              Priorizar ETFs nas compras
            </label>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-primary" onClick={load} disabled={loading}>
            {loading ? 'Calculando...' : 'Calcular'}
          </button>
          <button
            className="btn btn-ghost"
            onClick={() => {
              setProfileOverride('');
              setAllowSells(true);
              setPreferEtfs(false);
              setMinTradeValue(100);
              setMaxTurnoverPercent(25);
            }}
            disabled={loading}
          >
            Redefinir
          </button>
        </div>
      </section>

      {error && (
        <div className="error-block" style={{ marginTop: 16 }}>
          {error}
        </div>
      )}

      {data && !loading && !error && (
        <>
          <section style={{ marginTop: 16 }}>
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 16,
                padding: 16,
                borderRadius: 12,
                background: '#101b22',
                border: '1px solid rgba(255,255,255,0.06)',
              }}
            >
              <Metric label="Valor total" value={formatCurrency(data.total_value)} />
              <Metric label="Valor pós-ajuste" value={formatCurrency(data.total_value_after)} />
              <Metric label="Turnover" value={formatPercent(data.turnover, 2)} />
              {netCashFlowLabel && <Metric label="Fluxo líquido" value={netCashFlowLabel} />}
              <Metric
                label="Situação"
                value={data.within_bands ? 'Carteira dentro das bandas alvo' : 'Ajustes recomendados'}
              />
            </div>
          </section>

          <section style={{ marginTop: 16 }}>
            <h3>Desvios por classe</h3>
            <div style={{ overflowX: 'auto' }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Classe</th>
                    <th>Atual</th>
                    <th>Alvo</th>
                    <th>Banda</th>
                    <th>Delta</th>
                    <th>Valor atual</th>
                    <th>Δ Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {classEntries.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="muted">
                        Sem dados de alocação disponíveis.
                      </td>
                    </tr>
                  ) : (
                    classEntries.map((entry) => (
                      <tr key={entry.key}>
                        <td>{CLASS_LABELS[entry.key] ?? entry.label ?? entry.key.toUpperCase()}</td>
                        <td>{formatPercent(entry.current_pct)}</td>
                        <td>{formatPercent(entry.target_pct)}</td>
                        <td>
                          {formatPercent(entry.floor_pct, 2)} a {formatPercent(entry.ceiling_pct, 2)}
                        </td>
                        <td style={{ color: entry.delta_pct >= 0 ? '#2e7d32' : '#c62828' }}>
                          {formatPercent(entry.delta_pct)}
                        </td>
                        <td>{formatCurrency(entry.current_value)}</td>
                        <td>{formatCurrency(entry.delta_value)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section style={{ marginTop: 16 }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 6,
                flexWrap: 'wrap',
                gap: 8,
              }}
            >
              <div className="muted">Sugestões de ordens</div>
              <button
                className="btn btn-success"
                onClick={handleApply}
                disabled={
                  applying || !data.suggestions || data.suggestions.length === 0
                }
              >
                {applying ? 'Aplicando...' : 'Aplicar plano'}
              </button>
            </div>
            {applyError && (
              <div className="error-block" style={{ marginBottom: 8 }}>
                {applyError}
              </div>
            )}
            {applyMessage && (
              <div
                style={{
                  marginBottom: 8,
                  padding: 8,
                  borderRadius: 8,
                  background: '#123d1f',
                  color: '#8cf29d',
                }}
              >
                {applyMessage}
              </div>
            )}
            <div style={{ overflowX: 'auto' }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Ativo</th>
                    <th>Classe</th>
                    <th>Ação</th>
                    <th>Quantidade</th>
                    <th>Valor</th>
                    <th>Preço ref.</th>
                    <th>Peso antes</th>
                    <th>Peso depois</th>
                    <th>Racional</th>
                  </tr>
                </thead>
                <tbody>
                  {data.suggestions.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="muted">
                        Sem ajustes sugeridos. Carteira dentro das bandas definidas.
                      </td>
                    </tr>
                  ) : (
                    data.suggestions.map((suggestion, index) => (
                      <tr key={`${suggestion.symbol}-${index}`}>
                        <td>
                          <b>{suggestion.symbol}</b>
                        </td>
                        <td>{CLASS_LABELS[suggestion.class] ?? suggestion.class.toUpperCase()}</td>
                        <td
                          style={{
                            color: suggestion.action === 'comprar' ? '#2e7d32' : '#c62828',
                            fontWeight: 700,
                          }}
                        >
                          {suggestion.action}
                        </td>
                        <td>{suggestion.quantity.toLocaleString('pt-BR', { maximumFractionDigits: 4 })}</td>
                        <td>{formatCurrency(suggestion.value)}</td>
                        <td>{formatCurrency(suggestion.price_ref)}</td>
                        <td>{formatPercent(suggestion.weight_before, 3)}</td>
                        <td>{formatPercent(suggestion.weight_after, 3)}</td>
                        <td style={{ maxWidth: 280 }}>{suggestion.rationale}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {data.candidates && Object.keys(data.candidates).length > 0 && (
            <section style={{ marginTop: 16 }}>
              <h3 style={{ marginBottom: 6 }}>Ativos sugeridos para analisar</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {Object.entries(data.candidates).map(([cls, items]) => (
                  <div
                    key={cls}
                    style={{
                      border: '1px solid rgba(255,255,255,0.08)',
                      borderRadius: 12,
                      padding: 12,
                    }}
                  >
                    <div style={{ fontWeight: 600, marginBottom: 8 }}>
                      {items[0]?.class_label ?? CLASS_LABELS[cls] ?? cls.toUpperCase()}
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {items.map((item) => (
                        <span
                          key={`${cls}-${item.symbol}`}
                          style={{
                            borderRadius: 999,
                            padding: '6px 12px',
                            background: '#1f2b33',
                            border: '1px solid rgba(255,255,255,0.08)',
                          }}
                        >
                          <strong>{item.symbol}</strong>
                          {item.description && (
                            <span className="muted" style={{ marginLeft: 6 }}>
                              {item.description}
                            </span>
                          )}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {data.notes.length > 0 && (
            <section style={{ marginTop: 16 }}>
              <div className="muted" style={{ marginBottom: 6 }}>
                Observações
              </div>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {data.notes.map((note, index) => (
                  <li key={index} style={{ marginBottom: 4 }}>
                    {note}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {data.rules_applied.length > 0 && (
            <section style={{ marginTop: 16 }}>
              <div className="muted" style={{ marginBottom: 6 }}>
                Regras de perfil aplicadas
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {data.rules_applied.map((rule) => (
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
            </section>
          )}
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <div className="muted" style={{ fontSize: 12 }}>
        {label}
      </div>
      <div style={{ fontWeight: 600 }}>{value ?? '--'}</div>
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

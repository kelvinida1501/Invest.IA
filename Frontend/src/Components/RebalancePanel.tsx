import React, { useEffect, useMemo, useState } from 'react';
import api from '../Api/ApiClient';

type RebalanceResp = {
  profile: 'conservador' | 'moderado' | 'arrojado' | string;
  total: number;
  targets: Record<string, number>; // ex: { acao: 0.45, etf: 0.10, fundo: 0.35, cripto: 0.10 }
  buckets: {
    values: Record<string, number>;
    pct: Record<string, number>;
  };
  suggestions: Array<{
    symbol: string;
    class: string;
    action: 'comprar' | 'vender' | string;
    delta_value: number;
    delta_qty: number;
    price_ref: number;
  }>;
};

export default function RebalancePanel() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<RebalanceResp | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [override, setOverride] = useState<string>(''); // "", "conservador", "moderado", "arrojado"

  const load = async () => {
  setLoading(true);
  setError(null);
  try {
    const qs = override ? `?profile_override=${override}` : '';
    const { data } = await api.get(`/portfolio/rebalance${qs}`);
    setData(data);
  } catch (err: any) {
    const detail =
      err?.response?.data?.detail ||
      err?.response?.data?.message ||
      `Falha ao calcular rebalanceamento (status ${err?.response?.status ?? '?'}).`;
    setError(detail);
    setData(null);
  } finally {
    setLoading(false);
  }
};
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const targetsPct = useMemo(() => {
    const t: Record<string, number> = {};
    if (data?.targets) {
      for (const k of Object.keys(data.targets)) t[k] = Math.round(data.targets[k] * 100);
    }
    return t;
  }, [data]);

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <div className="muted" style={{ fontSize: 12 }}>
          Perfil atual:
        </div>
        <b>{data?.profile ?? '—'}</b>
        <div style={{ flex: 1 }} />
        <select value={override} onChange={(e) => setOverride(e.target.value)} className="input" style={{ maxWidth: 220 }}>
          <option value="">Sem override (usar perfil salvo)</option>
          <option value="conservador">conservador</option>
          <option value="moderado">moderado</option>
          <option value="arrojado">arrojado</option>
        </select>
        <button className="btn btn-ghost" onClick={load}>Calcular</button>
      </div>

      {loading && <p className="muted" style={{ marginTop: 8 }}>Calculando…</p>}

      {data && !loading && (
        <>
          {/* Buckets atuais vs alvo */}
          <div style={{ marginTop: 12, overflowX: 'auto' }}>
            <table className="table">
              <thead>
                  {error && (
                    <div style={{ marginTop: 8, color: '#c62828' }}>
                      {error}
                    </div>
                  )}
                <tr>
                  <th>Bucket</th>
                  <th>Atual (%)</th>
                  <th>Alvo (%)</th>
                  <th>Valor atual (R$)</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(targetsPct).map((b) => (
                  <tr key={b}>
                    <td><b>{b}</b></td>
                    <td>{(data.buckets?.pct?.[b] ?? 0).toFixed(2)}%</td>
                    <td>{targetsPct[b]}%</td>
                    <td>R$ {(data.buckets?.values?.[b] ?? 0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Sugestões por ativo */}
          <div style={{ marginTop: 12 }}>
            <div className="muted" style={{ marginBottom: 6 }}>
              Sugestões (ordenadas por maior ajuste de valor)
            </div>
            {data.suggestions.length === 0 ? (
              <p className="muted">Sem ajustes sugeridos.</p>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Ativo</th>
                      <th>Bucket</th>
                      <th>Ação</th>
                      <th>Qtd</th>
                      <th>Valor (R$)</th>
                      <th>Preço ref. (R$)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.suggestions.map((s, i) => (
                      <tr key={i}>
                        <td><b>{s.symbol}</b></td>
                        <td>{s.class}</td>
                        <td style={{ color: s.action === 'comprar' ? '#2e7d32' : '#c62828', fontWeight: 700 }}>
                          {s.action}
                        </td>
                        <td>{s.delta_qty.toFixed(4)}</td>
                        <td>R$ {s.delta_value.toFixed(2)}</td>
                        <td>R$ {s.price_ref.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

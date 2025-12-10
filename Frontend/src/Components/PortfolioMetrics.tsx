import React from 'react';
import { PortfolioSummary } from '../types/portfolio';
import UpdateBadge from './UpdateBadge';

type Props = {
  summary: PortfolioSummary | null;
  loading: boolean;
};

function formatCurrency(value: number, currency: string) {
  if (value == null || Number.isNaN(value)) return '-';
  return value.toLocaleString('pt-BR', {
    style: 'currency',
    currency,
    maximumFractionDigits: 2,
  });
}

function formatPercent(value?: number | null) {
  if (value == null || Number.isNaN(value)) return '-';
  return `${value.toFixed(2)}%`;
}

function trendClass(value: number | undefined | null) {
  if (value == null) return '';
  if (value > 0) return 'positive';
  if (value < 0) return 'negative';
  return '';
}

export default function PortfolioMetrics({ summary, loading }: Props) {
  const baseCurrency = summary?.base_currency ?? 'BRL';
  const kpis = summary?.kpis;
  const itens = summary?.itens ?? [];

  const metrics = React.useMemo(() => {
    if (!summary || !kpis) return null;
    return [
      {
        key: 'invested_total',
        label: 'Investido',
        value: formatCurrency(kpis.invested_total, baseCurrency),
      },
      {
        key: 'market_total',
        label: 'Valor de mercado',
        value: formatCurrency(kpis.market_total, baseCurrency),
      },
      {
        key: 'pnl_total',
        label: 'P/L total',
        value: formatCurrency(kpis.pnl_abs, baseCurrency),
        extra: formatPercent(kpis.pnl_pct),
        trend: kpis.pnl_abs,
      },
      {
        key: 'pnl_unrealized',
        label: 'P/L não realizado',
        value: formatCurrency(kpis.pnl_unrealized_abs, baseCurrency),
        extra: formatPercent(kpis.pnl_unrealized_pct),
        trend: kpis.pnl_unrealized_abs,
      },
      {
        key: 'pnl_realized',
        label: 'P/L realizado',
        value: formatCurrency(kpis.pnl_realized_abs, baseCurrency),
        extra: formatPercent(kpis.pnl_realized_pct),
        trend: kpis.pnl_realized_abs,
      },
      {
        key: 'day_change',
        label: 'Variação do dia',
        value: formatCurrency(kpis.day_change_abs, baseCurrency),
        extra: formatPercent(kpis.day_change_pct),
        trend: kpis.day_change_abs,
      },
      {
        key: 'positions',
        label: 'Ativos na carteira',
        value: itens.length.toString(),
      },
    ];
  }, [summary, kpis, baseCurrency, itens.length]);

  return (
    <section className="metrics-card card">
      <div className="card-header">
        <div className="card-header-left">
          <h2>Indicadores gerais</h2>
          <UpdateBadge asOf={summary?.as_of ?? null} loading={loading} />
        </div>
      </div>

      {!summary || !metrics ? (
        <p className="muted">{loading ? 'Carregando carteira...' : 'Sem dados de carteira.'}</p>
      ) : (
        <div className="metrics-grid">
          {metrics.map((metric) => (
            <div key={metric.key} className="metric">
              <span className="metric-label">{metric.label}</span>
              <strong className={`metric-value ${trendClass(metric.trend)}`}>
                {metric.value}
              </strong>
              {metric.extra ? <span className="metric-extra">{metric.extra}</span> : null}
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

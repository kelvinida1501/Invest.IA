import React from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import api from '../Api/ApiClient';
import { PortfolioTimeseries } from '../types/portfolio';

const RANGE_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '1M', label: '1M' },
  { value: '3M', label: '3M' },
  { value: '6M', label: '6M' },
  { value: '1A', label: '1A' },
  { value: '5A', label: '5A' },
  { value: 'YTD', label: 'YTD' },
  { value: 'ALL', label: 'Tudo' },
];

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 2,
});

const dateFormatter = new Intl.DateTimeFormat('pt-BR', {
  day: '2-digit',
  month: 'short',
});

type SeriesVisibility = {
  market: boolean;
  invested: boolean;
  pnlTotal: boolean;
  pnlUnrealized: boolean;
  pnlRealized: boolean;
};

function formatCurrency(value: number | null | undefined) {
  if (value == null) return 'R$ 0,00';
  return currencyFormatter.format(value);
}

function parseDateLocal(dateStr: string) {
  if (!dateStr) return null;
  const parts = dateStr.split('-').map((part) => Number(part));
  if (parts.length !== 3 || parts.some((num) => Number.isNaN(num))) {
    return null;
  }
  const [year, month, day] = parts;
  return new Date(year, month - 1, day);
}

function formatDateLabel(dateStr: string) {
  const parsed = parseDateLocal(dateStr);
  if (!parsed) return dateStr;
  return dateFormatter.format(parsed);
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
      <div className="tooltip-card">
        <div className="tooltip-title">
          {parseDateLocal(label)?.toLocaleDateString('pt-BR', {
            day: '2-digit',
            month: 'long',
            year: 'numeric',
          }) ?? label}
        </div>
      {payload.map((entry: any) => (
        <div key={entry.name} className="tooltip-row">
          <span>{entry.name}</span>
          <strong>{formatCurrency(entry.value)}</strong>
        </div>
      ))}
    </div>
  );
};

type EvolutionProps = {
  refreshKey?: number;
};

export default function PortfolioEvolutionChart({ refreshKey = 0 }: EvolutionProps) {
  const [range, setRange] = React.useState<string>('6M');
  const [timeseries, setTimeseries] = React.useState<PortfolioTimeseries | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [visibility, setVisibility] = React.useState<SeriesVisibility>({
    market: true,
    invested: true,
    pnlTotal: false,
    pnlUnrealized: false,
    pnlRealized: false,
  });

  const loadData = React.useCallback(
    async (selectedRange: string) => {
      setLoading(true);
      setError(null);
      try {
        const { data } = await api.get<PortfolioTimeseries>('/portfolio/timeseries', {
          params: { range: selectedRange },
        });
        setTimeseries(data);
      } catch (err: any) {
        console.error('Erro ao carregar evolucao da carteira', err);
        setError(err?.response?.data?.detail || 'Falha ao carregar evolucao da carteira.');
      } finally {
        setLoading(false);
      }
    },
    []
  );

  React.useEffect(() => {
    loadData(range);
  }, [range, loadData, refreshKey]);

  const toggleSeries = (key: keyof SeriesVisibility) => {
    setVisibility((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const chartData = React.useMemo(() => timeseries?.series ?? [], [timeseries]);
  const earliestDate = timeseries?.earliest_date;
  const startDate = timeseries?.start_date;
  const asOf = timeseries?.as_of;

  return (
    <div className="portfolio-evolution">
      <div className="evolution-toolbar">
        <div className="chip-group">
          {RANGE_OPTIONS.map((option) => (
            <button
              key={option.value}
              className={`chip ${range === option.value ? 'active' : ''}`}
              onClick={() => setRange(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
        <div className="series-toggles">
          <label>
            <input
              type="checkbox"
              checked={visibility.market}
              onChange={() => toggleSeries('market')}
            />
            Valor de mercado
          </label>
          <label>
            <input
              type="checkbox"
              checked={visibility.invested}
              onChange={() => toggleSeries('invested')}
            />
            Aportes líquidos
          </label>
          <label>
            <input
              type="checkbox"
              checked={visibility.pnlTotal}
              onChange={() => toggleSeries('pnlTotal')}
            />
            P/L total
          </label>
          <label>
            <input
              type="checkbox"
              checked={visibility.pnlUnrealized}
              onChange={() => toggleSeries('pnlUnrealized')}
            />
            P/L não realizado
          </label>
          <label>
            <input
              type="checkbox"
              checked={visibility.pnlRealized}
              onChange={() => toggleSeries('pnlRealized')}
            />
            P/L realizado
          </label>
        </div>
      </div>

      {loading ? (
        <p className="muted">Carregando evolucao da carteira...</p>
      ) : error ? (
        <div className="alert alert-error">
          <span>{error}</span>
          <button className="btn btn-ghost" onClick={() => loadData(range)}>
            Tentar novamente
          </button>
        </div>
      ) : chartData.length === 0 ? (
        <p className="muted">Sem dados suficientes para gerar o grafico.</p>
      ) : (
        <div className="chart-wrapper">
          <ResponsiveContainer width="100%" height={360}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.2} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDateLabel}
                minTickGap={32}
              />
              <YAxis tickFormatter={(value) => currencyFormatter.format(value)} width={90} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              {visibility.market && (
                <Area
                  type="monotone"
                  dataKey="market_value"
                  name="Valor de mercado"
                  stroke="#f2b705"
                  fill="#f2b70533"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              )}
              {visibility.invested && (
                <Line
                  type="monotone"
                  dataKey="invested"
                  name="Aportes líquidos"
                  stroke="#4cafef"
                  strokeWidth={2}
                  dot={false}
                />
              )}
              {visibility.pnlTotal && (
                <Line
                  type="monotone"
                  dataKey="pnl_total"
                  name="P/L total"
                  stroke="#2e7d32"
                  strokeWidth={2}
                  dot={false}
                />
              )}
              {visibility.pnlUnrealized && (
                <Line
                  type="monotone"
                  dataKey="pnl_unrealized"
                  name="P/L não realizado"
                  stroke="#ef6c00"
                  strokeWidth={2}
                  dot={false}
                />
              )}
              {visibility.pnlRealized && (
                <Line
                  type="monotone"
                  dataKey="pnl_realized"
                  name="P/L realizado"
                  stroke="#8e24aa"
                  strokeWidth={2}
                  dot={false}
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="evolution-meta muted small">
        {startDate ? (
          <span>
            Inicio: {parseDateLocal(startDate)?.toLocaleDateString('pt-BR') ?? startDate}
            {earliestDate && startDate !== earliestDate
              ? ` (primeira compra em ${
                  parseDateLocal(earliestDate)?.toLocaleDateString('pt-BR') ?? earliestDate
                })`
              : ''}
          </span>
        ) : earliestDate ? (
          <span>
            Primeira compra em{' '}
            {parseDateLocal(earliestDate)?.toLocaleDateString('pt-BR') ?? earliestDate}
          </span>
        ) : null}
        {asOf ? (
          <span>Atualizado em {parseDateLocal(asOf)?.toLocaleDateString('pt-BR') ?? asOf}</span>
        ) : null}
      </div>
    </div>
  );
}

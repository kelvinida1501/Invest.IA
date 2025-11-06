import React from 'react';
import api from '../Api/ApiClient';
import AllocationChart from './AllocationChart';
import {
  AllocationAssetItem,
  AllocationClassItem,
  AllocationResponse,
  PortfolioSummary,
} from '../types/portfolio';
import UpdateBadge from './UpdateBadge';

const MODE_OPTIONS: Array<{ value: 'class' | 'asset'; label: string }> = [
  { value: 'class', label: 'Por classe' },
  { value: 'asset', label: 'Por ativo' },
];

const CLASS_LABELS: Record<string, string> = {
  acao: 'Ações',
  etf: 'ETFs',
  fii: 'Fundos imobiliários',
  fundo: 'Fundos',
  cripto: 'Cripto',
  renda_fixa: 'Renda fixa',
  caixa: 'Caixa',
  outros: 'Outros',
};

type Props = {
  refreshKey: number | string;
  summary: PortfolioSummary | null;
};

function formatCurrency(value: number) {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function resolveClassLabel(value: string | undefined | null) {
  const normalized = value?.toLowerCase?.() ?? '';
  return CLASS_LABELS[normalized] ?? normalized.toUpperCase();
}

export default function AllocationPanel({ refreshKey, summary }: Props) {
  const [mode, setMode] = React.useState<'class' | 'asset'>('class');
  const [classFilter, setClassFilter] = React.useState<string>('todos');
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [allocation, setAllocation] = React.useState<AllocationResponse | null>(null);

  const appliedClass = React.useMemo(
    () => (allocation?.applied_class ? resolveClassLabel(allocation.applied_class) : 'Todos'),
    [allocation]
  );

  React.useEffect(() => {
    if (mode === 'class') {
      setClassFilter('todos');
    }
  }, [mode]);

  const availableClasses = React.useMemo(() => {
    if (!allocation) return [];
    return Array.from(new Set(allocation.available_classes))
      .map((value) => ({
        value,
        label: resolveClassLabel(value),
      }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [allocation]);

  const chartData = React.useMemo(() => {
    if (!allocation) return [];
    const items = allocation.items;

    const isAssetItems = (data: AllocationResponse['items']): data is AllocationAssetItem[] =>
      data.length > 0 && Object.prototype.hasOwnProperty.call(data[0], 'symbol');

    if (!isAssetItems(items)) {
      const classItems = items as AllocationClassItem[];
      return classItems.map((item, index) => {
        const key = item.class ?? `classe-${index}`;
        return {
          key,
          label: resolveClassLabel(item.class),
          value: item.value,
          weight_pct: item.weight_pct,
          class: item.class,
        };
      });
    }

    const assetItems = items as AllocationAssetItem[];
    return assetItems.map((item, index) => ({
      key: item.symbol ? `asset-${item.symbol}` : `asset-${index}`,
      label: item.symbol ?? item.name ?? `Ativo ${index + 1}`,
      value: item.value,
      weight_pct: item.weight_pct,
      class: item.class,
    }));
  }, [allocation]);

  const handleFetch = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = { mode };
      if (mode === 'asset' && classFilter !== 'todos') {
        params.class = classFilter;
      }
      if (mode === 'asset') {
        params.group_small = 0.02;
      }
      const { data } = await api.get<AllocationResponse>('/portfolio/allocation', { params });
      setAllocation(data);
    } catch (err) {
      console.error('Erro ao carregar alocação', err);
      setError('Não foi possível carregar a alocação.');
    } finally {
      setLoading(false);
    }
  }, [mode, classFilter]);

  React.useEffect(() => {
    handleFetch();
  }, [handleFetch, refreshKey]);

  const totalLabel = React.useMemo(() => {
    if (allocation?.total) {
      return formatCurrency(allocation.total);
    }
    if (summary?.market_total) {
      return formatCurrency(summary.market_total);
    }
    return 'R$ 0,00';
  }, [allocation, summary]);

  return (
    <div className="allocation-panel">
      <div className="allocation-header">
        <div className="allocation-header-left">
          <div className="allocation-title">
            <h3>Distribuição da carteira</h3>
            <span className="muted small">Total: {totalLabel}</span>
          </div>
          <div className="allocation-modes">
            {MODE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                className={`chip ${mode === opt.value ? 'active' : ''}`}
                onClick={() => setMode(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
        <UpdateBadge asOf={allocation?.as_of ?? summary?.as_of ?? null} loading={loading} />
      </div>

      {mode === 'asset' && availableClasses.length > 0 && (
        <div className="allocation-filters">
          <span className="muted small">Classe:</span>
          <div className="chip-group scrollable">
            <button
              className={`chip ${classFilter === 'todos' ? 'active' : ''}`}
              onClick={() => setClassFilter('todos')}
            >
              Todos
            </button>
            {availableClasses.map((cls) => (
              <button
                key={cls.value}
                className={`chip ${classFilter === cls.value ? 'active' : ''}`}
                onClick={() => setClassFilter(cls.value)}
              >
                {cls.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {error ? (
        <div className="alert alert-error">
          <span>{error}</span>
          <button className="btn btn-ghost" onClick={handleFetch}>
            Tentar novamente
          </button>
        </div>
      ) : loading ? (
        <div className="allocation-loading">Calculando alocação...</div>
      ) : (
        <AllocationChart data={chartData} mode={mode} />
      )}

      {mode === 'asset' && (
        <p className="muted small">
          Mostrando {chartData.length} grupos — Classe selecionada: {appliedClass}
        </p>
      )}
    </div>
  );
}

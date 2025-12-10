import React from 'react';
import { PortfolioHolding } from '../types/portfolio';

type SortKey =
  | 'symbol'
  | 'class'
  | 'quantity'
  | 'avg_price'
  | 'last_price'
  | 'valor'
  | 'pct'
  | 'pnl_pct'
  | 'day_change_pct';

type Props = {
  holdings: PortfolioHolding[];
  loading?: boolean;
  compact?: boolean;
  enableFilters?: boolean;
  headline?: string;
};

const CLASS_LABELS: Record<string, string> = {
  acao: 'Ações',
  etf: 'ETF',
  fii: 'FII',
  fundo: 'Fundo',
  cripto: 'Cripto',
  renda_fixa: 'Renda fixa',
  caixa: 'Caixa',
  outros: 'Outros',
};

function formatCurrency(value: number | undefined) {
  if (value == null) return '-';
  return value.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 2,
  });
}

function formatNumber(value: number | undefined, digits = 2) {
  if (value == null) return '-';
  return value.toLocaleString('pt-BR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatPercent(value: number | undefined) {
  if (value == null) return '-';
  return `${value.toFixed(2)}%`;
}

function classLabel(value: string | undefined) {
  if (!value) return '-';
  return CLASS_LABELS[value] ?? value.toUpperCase();
}

function trendClass(value: number | undefined) {
  if (value == null) return '';
  if (value > 0) return 'positive';
  if (value < 0) return 'negative';
  return '';
}

export default function PortfolioPositionsTable({
  holdings,
  loading = false,
  compact = false,
  enableFilters = true,
  headline,
}: Props) {
  const [sortKey, setSortKey] = React.useState<SortKey>('valor');
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('desc');
  const [classFilter, setClassFilter] = React.useState<string>('todos');
  const [search, setSearch] = React.useState('');

  const classes = React.useMemo(() => {
    const unique = new Set<string>();
    holdings.forEach((item) => {
      if (item.class) unique.add(item.class);
    });
    return Array.from(unique).sort((a, b) =>
      a.localeCompare(b, 'pt-BR', { sensitivity: 'base' })
    );
  }, [holdings]);

  const filtered = React.useMemo(() => {
    let rows = holdings;
    if (enableFilters && classFilter !== 'todos') {
      rows = rows.filter((item) => item.class === classFilter);
    }
    if (search.trim()) {
      const term = search.trim().toLowerCase();
      rows = rows.filter(
        (item) =>
          item.symbol.toLowerCase().includes(term) ||
          (item.name ?? '').toLowerCase().includes(term)
      );
    }
    return rows;
  }, [holdings, classFilter, enableFilters, search]);

  const sorted = React.useMemo(() => {
    return [...filtered].sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1;
      const valA = (a as any)[sortKey] ?? 0;
      const valB = (b as any)[sortKey] ?? 0;
      if (typeof valA === 'string' && typeof valB === 'string') {
        return dir * valA.localeCompare(valB);
      }
      return dir * ((Number(valA) || 0) - (Number(valB) || 0));
    });
  }, [filtered, sortKey, sortDir]);

  const rows = sorted;

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  return (
    <div className={`positions-table ${compact ? 'compact' : ''}`}>
      {headline ? <h3>{headline}</h3> : null}

      {enableFilters && (
        <div className="positions-toolbar">
          <div className="chip-group">
            <button
              className={`chip ${classFilter === 'todos' ? 'active' : ''}`}
              onClick={() => setClassFilter('todos')}
            >
              Todos
            </button>
            {classes.map((cls) => (
              <button
                key={cls}
                className={`chip ${classFilter === cls ? 'active' : ''}`}
                onClick={() => setClassFilter(cls)}
              >
                {classLabel(cls)}
              </button>
            ))}
          </div>
          <input
            type="search"
            value={search}
            onChange={(evt) => setSearch(evt.target.value)}
            placeholder="Buscar ticker"
          />
        </div>
      )}

      {loading ? (
        <p className="muted">Carregando ativos...</p>
      ) : rows.length === 0 ? (
        <p className="muted">Nenhum ativo encontrado.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th onClick={() => handleSort('symbol')}>Ativo</th>
                <th onClick={() => handleSort('class')}>Classe</th>
                {!compact && <th onClick={() => handleSort('quantity')}>Qtde</th>}
                {!compact && <th onClick={() => handleSort('avg_price')}>PM</th>}
                <th onClick={() => handleSort('last_price')}>Preço</th>
                <th onClick={() => handleSort('valor')}>Valor</th>
                <th onClick={() => handleSort('pct')}>Part. %</th>
                <th onClick={() => handleSort('pnl_pct')}>P/L %</th>
                <th onClick={() => handleSort('day_change_pct')}>Var. dia %</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => (
                <tr key={item.holding_id}>
                  <td>
                    <strong>{item.symbol}</strong>
                    {item.name ? <div className="muted small">{item.name}</div> : null}
                  </td>
                  <td>{classLabel(item.class)}</td>
                  {!compact && <td>{formatNumber(item.quantity)}</td>}
                  {!compact && <td>{formatCurrency(item.avg_price)}</td>}
                  <td>{formatCurrency(item.last_price)}</td>
                  <td>{formatCurrency(item.valor)}</td>
                  <td>{formatPercent(item.pct)}</td>
                  <td className={trendClass(item.pnl_pct)}>{formatPercent(item.pnl_pct)}</td>
                  <td className={trendClass(item.day_change_pct)}>
                    {formatPercent(item.day_change_pct)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

import React from 'react';
import api from '../Api/ApiClient';

type Transaction = {
  id: number;
  symbol: string;
  name: string;
  type: 'buy' | 'sell';
  quantity: number;
  price: number;
  total: number;
  executed_at: string;
  status: 'active' | 'voided';
  kind: 'trade' | 'adjust';
  source?: string | null;
  note?: string | null;
  reversal_of_id?: number | null;
};

type Filters = {
  start: string;
  end: string;
  limit: number;
  status: 'active' | 'voided' | 'all';
  kind: 'trade' | 'adjust' | 'all';
};

const QUICK_RANGES: Array<{ label: string; days: number | null }> = [
  { label: '7D', days: 7 },
  { label: '30D', days: 30 },
  { label: '90D', days: 90 },
  { label: '1A', days: 365 },
  { label: 'Tudo', days: null },
];

const LIMIT_OPTIONS = [25, 50, 100, 200];
const STATUS_OPTIONS: Array<{ value: Filters['status']; label: string }> = [
  { value: 'active', label: 'Ativas' },
  { value: 'voided', label: 'Anuladas' },
  { value: 'all', label: 'Todas' },
];
const KIND_OPTIONS: Array<{ value: Filters['kind']; label: string }> = [
  { value: 'all', label: 'Todas' },
  { value: 'trade', label: 'Trade' },
  { value: 'adjust', label: 'Ajuste' },
];

const kindLabels: Record<Transaction['kind'], string> = {
  trade: 'Trade',
  adjust: 'Ajuste',
};

const statusLabels: Record<Transaction['status'], string> = {
  active: 'Ativa',
  voided: 'Anulada',
};

const typeLabels: Record<Transaction['type'], string> = {
  buy: 'Compra',
  sell: 'Venda',
};

function formatQuantityValue(value: number) {
  const abs = Math.abs(value);
  let maxFractionDigits = 2;
  if (abs < 1 && abs >= 0.01) {
    maxFractionDigits = 4;
  } else if (abs < 0.01) {
    maxFractionDigits = 8;
  }
  return value.toLocaleString('pt-BR', {
    minimumFractionDigits: Math.min(2, maxFractionDigits),
    maximumFractionDigits: maxFractionDigits,
  });
}

function formatDateTime(iso: string) {
  if (!iso) return '-';
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return iso;
  }
  return parsed.toLocaleDateString('pt-BR', { timeZone: 'UTC' });
}

function toInputDate(date: Date) {
  const year = date.getFullYear();
  const month = `${date.getMonth() + 1}`.padStart(2, '0');
  const day = `${date.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

type ApiResponse = {
  items: Transaction[];
  total: number;
  limit: number;
  offset: number;
};

type Props = {
  refreshKey?: number;
  onChange?: () => void;
};

export default function TransactionsHistory({ refreshKey = 0, onChange }: Props) {
  const defaultFilters = React.useMemo<Filters>(
    () => ({
      start: '',
      end: '',
      limit: 50,
      status: 'active',
      kind: 'all',
    }),
    []
  );

  const [filters, setFilters] = React.useState<Filters>(defaultFilters);
  const [appliedFilters, setAppliedFilters] = React.useState<Filters>(defaultFilters);
  const [transactions, setTransactions] = React.useState<Transaction[]>([]);
  const [total, setTotal] = React.useState(0);
  const [offset, setOffset] = React.useState(0);
  const [loading, setLoading] = React.useState(true);
  const [loadingMore, setLoadingMore] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const [editingTx, setEditingTx] = React.useState<Transaction | null>(null);
  const [editForm, setEditForm] = React.useState({
    quantity: '',
    executed_at: '',
    type: 'buy' as Transaction['type'],
    kind: 'trade' as Transaction['kind'],
    note: '',
  });
  const [editError, setEditError] = React.useState<string | null>(null);
  const [savingEdit, setSavingEdit] = React.useState(false);

  const [voidingTx, setVoidingTx] = React.useState<Transaction | null>(null);
  const [voidNote, setVoidNote] = React.useState('');
  const [voidError, setVoidError] = React.useState<string | null>(null);
  const [voidLoading, setVoidLoading] = React.useState(false);

  const fetchTransactions = React.useCallback(
    async (filterState: Filters, nextOffset: number, append: boolean) => {
      if (append) {
        setLoadingMore(true);
      } else {
        setLoading(true);
        setError(null);
      }

      try {
        const params: Record<string, any> = {
          limit: filterState.limit,
          offset: nextOffset,
          status: filterState.status,
          kind: filterState.kind,
        };
        if (filterState.start) params.start = filterState.start;
        if (filterState.end) params.end = filterState.end;

        const { data } = await api.get<ApiResponse>('/portfolio/transactions', { params });

        setTransactions((prev) => (append ? [...prev, ...data.items] : data.items));
        setTotal(data.total);
        setOffset(nextOffset + data.items.length);
      } catch (err: any) {
        console.error('Erro ao carregar transações', err);
        setError(err?.response?.data?.detail || 'Falha ao carregar histórico.');
      } finally {
        if (append) {
          setLoadingMore(false);
        } else {
          setLoading(false);
        }
      }
    },
    []
  );

  React.useEffect(() => {
    fetchTransactions(appliedFilters, 0, false);
  }, [fetchTransactions, appliedFilters, refreshKey]);

  React.useEffect(() => {
    if (editingTx) {
      setEditForm({
        quantity: String(editingTx.quantity),
        executed_at: editingTx.executed_at ? editingTx.executed_at.slice(0, 10) : '',
        type: editingTx.type,
        kind: editingTx.kind,
        note: editingTx.note ?? '',
      });
      setEditError(null);
    }
  }, [editingTx]);

  React.useEffect(() => {
    if (voidingTx) {
      setVoidNote('');
      setVoidError(null);
    }
  }, [voidingTx]);

  const applyFilters = React.useCallback(() => {
    setAppliedFilters(filters);
  }, [filters]);

  const clearFilters = () => {
    setFilters(defaultFilters);
    setAppliedFilters(defaultFilters);
  };

  const handleQuickRange = (days: number | null) => {
    if (days === null) {
      const updated = { ...filters, start: '', end: '' };
      setFilters(updated);
      setAppliedFilters(updated);
      return;
    }

    const now = new Date();
    const startDate = new Date(now);
    startDate.setDate(startDate.getDate() - days);
    const startStr = toInputDate(startDate);
    const endStr = toInputDate(now);
    const updated = { ...filters, start: startStr, end: endStr };
    setFilters(updated);
    setAppliedFilters(updated);
  };

  const loadMore = () => {
    fetchTransactions(appliedFilters, offset, true);
  };

  const hasMore = offset < total;

  const handleEditSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!editingTx) return;
    setSavingEdit(true);
    setEditError(null);

    const quantity = Number(editForm.quantity);

    if (Number.isNaN(quantity) || quantity <= 0) {
      setEditError('Quantidade deve ser maior que zero.');
      setSavingEdit(false);
      return;
    }

    const payload: Record<string, any> = {
      quantity,
      type: editForm.type,
      kind: editForm.kind,
    };

    if (editForm.executed_at) {
      payload.executed_at = `${editForm.executed_at}T00:00:00`;
    }

    if (editForm.note.trim()) {
      payload.note = editForm.note.trim();
    } else {
      payload.note = '';
    }

    try {
      await api.patch(`/portfolio/transactions/${editingTx.id}`, payload);
      await fetchTransactions(appliedFilters, 0, false);
      setEditingTx(null);
      onChange?.();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setEditError(typeof detail === 'string' ? detail : 'Não foi possível atualizar a transação.');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleVoidConfirm = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!voidingTx) return;
    setVoidLoading(true);
    setVoidError(null);

    const payload = voidNote.trim() ? { note: voidNote.trim() } : {};

    try {
      await api.post(`/portfolio/transactions/${voidingTx.id}/void`, payload);
      await fetchTransactions(appliedFilters, 0, false);
      setVoidingTx(null);
      onChange?.();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setVoidError(typeof detail === 'string' ? detail : 'Não foi possível anular a transação.');
    } finally {
      setVoidLoading(false);
    }
  };

  return (
    <div className="transactions-card">
      <div className="transactions-toolbar">
        <div className="chip-group">
          {QUICK_RANGES.map((range) => (
            <button
              key={range.label}
              className="chip"
              onClick={() => handleQuickRange(range.days)}
            >
              {range.label}
            </button>
          ))}
        </div>
        <div className="transactions-filters">
          <label>
            Inicio
            <input
              type="date"
              value={filters.start}
              onChange={(evt) => setFilters((prev) => ({ ...prev, start: evt.target.value }))}
            />
          </label>
          <label>
            Fim
            <input
              type="date"
              value={filters.end}
              onChange={(evt) => setFilters((prev) => ({ ...prev, end: evt.target.value }))}
            />
          </label>
          <label>
            Status
            <select
              className="input"
              value={filters.status}
              onChange={(evt) =>
                setFilters((prev) => ({ ...prev, status: evt.target.value as Filters['status'] }))
              }
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Categoria
            <select
              className="input"
              value={filters.kind}
              onChange={(evt) =>
                setFilters((prev) => ({ ...prev, kind: evt.target.value as Filters['kind'] }))
              }
            >
              {KIND_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Limite
            <select
              className="input"
              value={filters.limit}
              onChange={(evt) =>
                setFilters((prev) => ({ ...prev, limit: Number(evt.target.value) }))
              }
            >
              {LIMIT_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <div className="filter-actions">
            <button className="btn btn-ghost" onClick={clearFilters}>
              Limpar
            </button>
            <button className="btn btn-secondary" onClick={applyFilters}>
              Aplicar
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <p className="muted">Carregando historico...</p>
      ) : error ? (
        <div>
          <p className="error">{error}</p>
          <button
            className="btn btn-ghost"
            onClick={() => fetchTransactions(appliedFilters, 0, false)}
          >
            Tentar novamente
          </button>
        </div>
      ) : transactions.length === 0 ? (
        <p className="muted">Nenhuma transação encontrada para o período selecionado.</p>
      ) : (
        <>
          <div className="transactions-summary muted small">
            Mostrando {transactions.length} de {total} registros
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Ativo</th>
                  <th>Tipo</th>
                  <th>Categoria</th>
                  <th>Status</th>
                  <th>Quantidade</th>
                  <th>Acoes</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr key={tx.id}>
                    <td>{formatDateTime(tx.executed_at)}</td>
                    <td>
                      <strong>{tx.symbol}</strong>
                      <div className="muted small">{tx.name}</div>
                      {tx.note ? (
                        <div className="muted small" style={{ fontStyle: 'italic' }}>
                          {tx.note}
                        </div>
                      ) : null}
                    </td>
                    <td style={{ textTransform: 'capitalize' }}>{typeLabels[tx.type]}</td>
                    <td>{kindLabels[tx.kind] ?? tx.kind}</td>
                    <td>
                      <span className={`status-badge ${tx.status}`}>{statusLabels[tx.status]}</span>
                    </td>
                    <td>{formatQuantityValue(tx.quantity)}</td>
                    <td>
                      <div className="table-actions">
                        <button
                          className="btn btn-ghost"
                          onClick={() => setEditingTx(tx)}
                          disabled={tx.status === 'voided'}
                        >
                          Editar
                        </button>
                        <button
                          className="btn btn-ghost"
                          onClick={() => setVoidingTx(tx)}
                          disabled={tx.status === 'voided'}
                        >
                          Anular
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {hasMore ? (
            <div className="transactions-actions">
              <button className="btn btn-ghost" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? 'Carregando...' : 'Carregar mais'}
              </button>
            </div>
          ) : null}
        </>
      )}

      {editingTx ? (
        <div className="modal-overlay">
          <div className="modal-card">
            <form onSubmit={handleEditSubmit}>
              <div className="modal-header">
                <h3>Editar transação</h3>
                <button
                  type="button"
                  className="modal-close"
                  onClick={() => setEditingTx(null)}
                >
                  —
              </button>
            </div>
            <div className="modal-body">
              <div className="modal-row">
                <label>Quantidade</label>
                <input
                  className="input"
                  type="number"
                  step="any"
                    min="0"
                    value={editForm.quantity}
                    onChange={(evt) =>
                      setEditForm((prev) => ({ ...prev, quantity: evt.target.value }))
                    }
                    required
                  />
              </div>
              <div className="modal-row">
                <label>Data</label>
                <input
                    className="input"
                    type="date"
                    value={editForm.executed_at}
                    onChange={(evt) =>
                      setEditForm((prev) => ({ ...prev, executed_at: evt.target.value }))
                    }
                  />
                </div>
                <div className="modal-row">
                  <label>Tipo</label>
                  <select
                    className="input"
                    value={editForm.type}
                    onChange={(evt) =>
                      setEditForm((prev) => ({
                        ...prev,
                        type: evt.target.value as Transaction['type'],
                      }))
                    }
                  >
                    <option value="buy">Compra</option>
                    <option value="sell">Venda</option>
                  </select>
                </div>
                <div className="modal-row">
                  <label>Categoria</label>
                  <select
                    className="input"
                    value={editForm.kind}
                    onChange={(evt) =>
                      setEditForm((prev) => ({
                        ...prev,
                        kind: evt.target.value as Transaction['kind'],
                      }))
                    }
                  >
                    <option value="trade">Trade</option>
                    <option value="adjust">Ajuste</option>
                  </select>
                </div>
                <div className="modal-row">
                  <label>Nota</label>
                  <textarea
                    className="input"
                    rows={3}
                    value={editForm.note}
                    onChange={(evt) =>
                      setEditForm((prev) => ({ ...prev, note: evt.target.value }))
                    }
                  />
                </div>
                {editError ? <p className="error">{editError}</p> : null}
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setEditingTx(null)}
                  disabled={savingEdit}
                >
                  Cancelar
                </button>
                <button type="submit" className="btn btn-secondary" disabled={savingEdit}>
                  {savingEdit ? 'Salvando...' : 'Salvar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}

      {voidingTx ? (
        <div className="modal-overlay">
          <div className="modal-card">
            <form onSubmit={handleVoidConfirm}>
              <div className="modal-header">
                <h3>Anular transação</h3>
                <button
                  type="button"
                  className="modal-close"
                  onClick={() => setVoidingTx(null)}
                >
                  —
                </button>
              </div>
              <div className="modal-body">
                <p>
                  Esta ação marca a transação <strong>#{voidingTx.id}</strong> como anulada. O
                  movimento deixara de impactar os calculos de evolucao da carteira.
                </p>
                <div className="modal-row">
                  <label>Nota (opcional)</label>
                  <textarea
                    className="input"
                    rows={3}
                    value={voidNote}
                    onChange={(evt) => setVoidNote(evt.target.value)}
                  />
                </div>
                {voidError ? <p className="error">{voidError}</p> : null}
              </div>
              <div className="modal-footer">
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => setVoidingTx(null)}
                  disabled={voidLoading}
                >
                  Cancelar
                </button>
                <button type="submit" className="btn btn-danger" disabled={voidLoading}>
                  {voidLoading ? 'Anulando...' : 'Confirmar anulação'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}



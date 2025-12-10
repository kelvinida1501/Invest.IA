import React, { useCallback, useEffect, useMemo, useState } from 'react';
import api from '../Api/ApiClient';
import type { PortfolioHolding as Holding } from '../types/portfolio';

type Props = {
  holdings: Holding[];
  onRefresh: () => void;
  onRegisterSearchTrigger?: (_open: () => void) => void;
};

type SearchResult = {
  symbol?: string;
  shortname?: string;
  longname?: string;
  exchange?: string;
  type?: string;
};

type QuoteState = {
  price: number | null;
  retrieved_at: string | null;
  loading: boolean;
  currency?: string | null;
  price_original?: number | null;
};

const QUOTE_TTL_MS = 5 * 60 * 1000;
const QUOTE_TOOLTIP =
  'Precos fornecidos pelo Yahoo Finance (yfinance). Podem conter atraso.';

const CLASSES = [
  { value: 'acao', label: 'Ação' },
  { value: 'etf', label: 'ETF' },
  { value: 'fundo', label: 'Fundo' },
  { value: 'cripto', label: 'Cripto' },
];

const CLASS_LABELS: Record<string, string> = {
  acao: 'Ação',
  etf: 'ETF',
  fundo: 'fundo',
  cripto: 'cripto',
};

const currencyFormatter = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
});

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

function isoTodayLocal() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function isFutureDate(dateStr: string) {
  if (!dateStr) return false;
  const input = new Date(dateStr);
  const today = new Date();
  input.setHours(0, 0, 0, 0);
  today.setHours(0, 0, 0, 0);
  return input.getTime() > today.getTime();
}

function toNumber(raw: string) {
  const normalized = raw.replace(/\./g, '').replace(',', '.');
  const parsed = parseFloat(normalized);
  return Number.isFinite(parsed) ? parsed : NaN;
}

function formatAgeLabel(minutes: number | null) {
  if (minutes == null) return 'Sem dados';
  if (minutes < 1) return 'menos de 1 min';
  if (minutes < 60) return `${Math.floor(minutes)} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    const remainder = Math.floor(minutes - hours * 60);
    return remainder > 0 ? `${hours}h ${remainder}min` : `${hours}h`;
  }
  const days = Math.floor(hours / 24);
  return days === 1 ? '1 dia' : `${days} dias`;
}

function parseLocalDate(iso: string) {
  const match = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) return new Date(iso);
  const [, year, month, day] = match;
  return new Date(Number(year), Number(month) - 1, Number(day));
}

function formatDateLabel(iso?: string | null) {
  if (!iso) return '-';
  const dt = parseLocalDate(iso);
  return Number.isNaN(dt.getTime()) ? iso : dt.toLocaleDateString('pt-BR');
}

function normalizeSymbol(symbol: string) {
  return symbol.trim().toUpperCase();
}

export default function HoldingsList({
  holdings,
  onRefresh,
  onRegisterSearchTrigger,
}: Props) {
  const todayStr = useMemo(isoTodayLocal, []);

  const [symbol, setSymbol] = useState('');
  const [quantity, setQuantity] = useState('');
  const [avgPrice, setAvgPrice] = useState('');
  const [purchaseDate, setPurchaseDate] = useState(todayStr);
  const [klass, setKlass] = useState('acao');

  const [editing, setEditing] = useState<number | null>(null);
  const [editQty, setEditQty] = useState('');
  const [editPrice, setEditPrice] = useState('');

  const [error, setError] = useState<string | null>(null);

  const [searchOpen, setSearchOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [sellTarget, setSellTarget] = useState<Holding | null>(null);
  const [sellQty, setSellQty] = useState('');
  const [sellPrice, setSellPrice] = useState('');
  const [sellDate, setSellDate] = useState(todayStr);
  const [sellError, setSellError] = useState<string | null>(null);
  const [sellLoading, setSellLoading] = useState(false);

  const [quoteMap, setQuoteMap] = useState<Record<string, QuoteState>>({});
  const [quoteError, setQuoteError] = useState<string | null>(null);
  const [bulkLoading, setBulkLoading] = useState(false);

  const openSearchModal = useCallback(() => {
    setSearchOpen(true);
    setSearchTerm('');
    setSearchResults([]);
    setSearchError(null);
  }, []);

  useEffect(() => {
    onRegisterSearchTrigger?.(openSearchModal);
  }, [openSearchModal, onRegisterSearchTrigger]);

  const resetForm = () => {
    setSymbol('');
    setQuantity('');
    setAvgPrice('');
    setPurchaseDate(todayStr);
    setKlass('acao');
  };

  const getQuoteInfo = useCallback(
    (holding: Holding) => {
      const key = normalizeSymbol(holding.symbol);
      const override = quoteMap[key];
      const price =
        override?.price ??
        (typeof holding.last_price === 'number' ? holding.last_price : null);
      const retrievedAt = override?.retrieved_at ?? holding.last_price_at ?? null;
      const loading = override?.loading ?? false;
      const currencyOverride = override?.currency ?? holding.currency;
      const originalOverride =
        override?.price_original ?? holding.last_price_original ?? null;
      const timestamp = retrievedAt ? Date.parse(retrievedAt) : Number.NaN;
      const ageMs = Number.isFinite(timestamp) ? Date.now() - timestamp : Number.POSITIVE_INFINITY;
      const isFresh = Number.isFinite(timestamp) && ageMs <= QUOTE_TTL_MS;
      const ageMinutes = Number.isFinite(timestamp) ? ageMs / 60000 : null;
      return {
        price,
        retrievedAt,
        loading,
        isFresh,
        ageMinutes,
        currency: currencyOverride,
        price_original: originalOverride,
      };
    },
    [quoteMap]
  );

  const markQuotesLoading = useCallback((symbols: string[], loading: boolean) => {
    const upper = symbols.map(normalizeSymbol);
    setQuoteMap((prev) => {
      const next = { ...prev };
      upper.forEach((sym) => {
        const current =
          next[sym] ?? { price: null, retrieved_at: null, loading: false, currency: null, price_original: null };
        next[sym] = { ...current, loading };
      });
      return next;
    });
  }, []);

  const refreshQuotes = useCallback(
    async (
      symbols: string[],
      options: { force?: boolean; silent?: boolean; bulk?: boolean } = {}
    ) => {
      const { force = false, silent = false, bulk = false } = options;
      if (!symbols.length) return;

      if (bulk) setBulkLoading(true);
      markQuotesLoading(symbols, true);
      if (!silent) setQuoteError(null);

      try {
        const { data } = await api.post('/prices/refresh', {
          symbols: symbols.map(normalizeSymbol),
          force,
        });
        const quotes = data?.quotes ?? {};
        setQuoteMap((prev) => {
          const next = { ...prev };
          Object.entries(quotes).forEach(([sym, payload]) => {
            const key = normalizeSymbol(sym);
            const value = typeof payload === 'object' && payload ? payload : {};
            const raw: any = value;
            next[key] = {
              price: typeof raw.price === 'number' ? Number(raw.price) : null,
              retrieved_at: raw.retrieved_at ?? null,
              loading: false,
              currency: typeof raw.currency === 'string' ? raw.currency : prev[key]?.currency ?? null,
              price_original:
                typeof raw.price_original === 'number'
                  ? Number(raw.price_original)
                  : prev[key]?.price_original ?? null,
            };
          });
          symbols.forEach((sym) => {
            const key = normalizeSymbol(sym);
            if (!next[key]) {
              next[key] = {
                price: null,
                retrieved_at: null,
                loading: false,
                currency: prev[key]?.currency ?? null,
                price_original: prev[key]?.price_original ?? null,
              };
            } else {
              next[key] = { ...next[key], loading: false };
            }
          });
          return next;
        });
        if (!silent) {
          onRefresh();
        }
      } catch (err: any) {
        console.error('Erro ao atualizar cotacao:', err);
        if (!silent) {
          setQuoteError(err?.response?.data?.detail || 'Falha ao atualizar preco.');
        }
        markQuotesLoading(symbols, false);
      } finally {
        if (bulk) setBulkLoading(false);
      }
    },
    [markQuotesLoading, onRefresh]
  );

  useEffect(() => {
    if (!holdings.length || searchOpen) return;
    const toRefresh = holdings
      .map((h) => ({ holding: h, info: getQuoteInfo(h) }))
      .filter(({ info }) => !info.loading && !info.isFresh)
      .map(({ holding }) => normalizeSymbol(holding.symbol));

    if (toRefresh.length) {
      const unique = Array.from(new Set(toRefresh));
      refreshQuotes(unique, { silent: true });
    }
  }, [getQuoteInfo, holdings, refreshQuotes, searchOpen]);

  const addHolding = async () => {
    if (!symbol || !quantity || !avgPrice || !purchaseDate) {
      setError('Preencha todos os campos.');
      return;
    }

    const qty = toNumber(quantity);
    const totalInvested = toNumber(avgPrice);
    if (!Number.isFinite(qty) || qty <= 0 || !Number.isFinite(totalInvested) || totalInvested <= 0) {
      setError('Quantidade e preço total devem ser números > 0.');
      return;
    }
    const unitPrice = totalInvested / qty;

    if (isFutureDate(purchaseDate)) {
      setError('A data de compra não pode ser futura.');
      return;
    }

    try {
      setError(null);

      const normalized = normalizeSymbol(symbol);

      // Impede novo lote exatamente no mesmo dia para o mesmo ativo
      const existsSameDay = holdings.some(
        (h) => normalizeSymbol(h.symbol) === normalized && (h.purchase_date || '') === purchaseDate
      );
      if (existsSameDay) {
        setError(`Já existe compra de ${normalized} em ${formatDateLabel(purchaseDate)}. Edite o registro existente.`);
        return;
      }
      let assetId: number;
      try {
        const res = await api.get('/assets', { params: { symbol: normalized } });
        assetId = res.data.id;
      } catch {
        const assetRes = await api.post('/assets', {
          symbol: normalized,
          name: normalized,
          class: klass,
        });
        assetId = assetRes.data.id;
      }

      await api.post('/holdings', {
        asset_id: assetId,
        quantity: qty,
        avg_price: unitPrice,
        purchase_date: purchaseDate,
      });

      resetForm();
      onRefresh();
    } catch (err: any) {
      console.error('Erro ao adicionar holding:', err);
      setError(err?.response?.data?.detail || 'Erro ao adicionar ativo.');
    }
  };

  const deleteHolding = async (id: number) => {
    try {
      await api.delete(`/holdings/${id}`);
      onRefresh();
    } catch (err) {
      console.error('Erro ao excluir holding:', err);
    }
  };

  const startEdit = (h: Holding) => {
    setEditing(h.holding_id);
    setEditQty(String(h.quantity));
    const totalInvested = h.avg_price * h.quantity;
    setEditPrice(totalInvested.toFixed(2).replace('.', ','));
    setError(null);
  };

  const saveEdit = async (id: number) => {
    const qty = toNumber(editQty);
    const total = toNumber(editPrice);
    if (!Number.isFinite(qty) || qty <= 0 || !Number.isFinite(total) || total <= 0) {
      setError('Quantidade e preço total devem ser números > 0.');
      return;
    }
    try {
      const unit = total / qty;
      await api.put(`/holdings/${id}`, { quantity: qty, avg_price: unit });
      setEditing(null);
      onRefresh();
    } catch (err) {
      console.error('Erro ao atualizar holding:', err);
    }
  };

  const openSellModal = (holding: Holding) => {
    setSellTarget(holding);
    setSellQty(String(holding.quantity));
    const defaultPrice = holding.last_price ?? holding.avg_price;
    setSellPrice(defaultPrice != null ? defaultPrice.toFixed(2).replace('.', ',') : '');
    setSellDate(todayStr);
    setSellError(null);
    setSellLoading(false);
  };

  const handleSell = async () => {
    if (!sellTarget) return;

    const qty = toNumber(sellQty);
    const price = toNumber(sellPrice);

    if (!Number.isFinite(qty) || qty <= 0) {
      setSellError('Informe uma quantidade válida.');
      return;
    }
    if (!Number.isFinite(price) || price <= 0) {
      setSellError('Informe um valor de venda válido.');
      return;
    }
    if (qty > sellTarget.quantity) {
      setSellError('Quantidade maior que a posição disponível.');
      return;
    }
    if (!sellDate || isFutureDate(sellDate)) {
      setSellError('A data de venda não pode ser futura.');
      return;
    }

    setSellLoading(true);
    try {
      await api.post(`/holdings/${sellTarget.holding_id}/sell`, {
        quantity: qty,
        price,
        sale_date: sellDate,
      });
      setSellTarget(null);
      onRefresh();
    } catch (err: any) {
      console.error('Erro ao vender holding:', err);
      setSellError(err?.response?.data?.detail || 'Falha ao registrar venda.');
    } finally {
      setSellLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchTerm.trim()) {
      setSearchError('Informe o ticker ou parte do nome.');
      setSearchResults([]);
      return;
    }
    setSearchLoading(true);
    setSearchError(null);
    try {
      const { data } = await api.get('/assets/search', {
        params: { q: searchTerm.trim(), limit: 10 },
      });
      setSearchResults(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Erro ao buscar no Yahoo:', err);
      setSearchError('Não foi possível consultar o Yahoo Finance.');
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  };

  const applySearchResult = (result: SearchResult) => {
    if (!result.symbol) return;
    setSymbol(result.symbol);
    setSearchOpen(false);
    setSearchResults([]);
  };

  const holdingsSymbols = useMemo(
    () => holdings.map((h) => normalizeSymbol(h.symbol)),
    [holdings]
  );

  const handleRefreshAll = () => {
    const unique = Array.from(new Set(holdingsSymbols));
    refreshQuotes(unique, { force: true, bulk: true });
  };

  const handleRowRefresh = (holding: Holding) => {
    refreshQuotes([holding.symbol], { force: true });
  };

  return (
    <div className="holdings-list">
      <div className="form-row holdings-form">
        <input
          className="input"
          placeholder="Ticker (ex: PETR4.SA)"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
        />

        <select
          className="input"
          value={klass}
          onChange={(e) => setKlass(e.target.value)}
          title="Classe do ativo"
        >
          {CLASSES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>

        <input
          className="input"
          placeholder="Quantidade"
          inputMode="decimal"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
        />
        <input
          className="input"
          placeholder="Valor total investido"
          inputMode="decimal"
          value={avgPrice}
          onChange={(e) => setAvgPrice(e.target.value)}
          title="Informe o valor total pago pela quantidade informada"
        />
        <input
          className="input"
          type="date"
          max={todayStr}
          value={purchaseDate}
          onChange={(e) => setPurchaseDate(e.target.value)}
        />
        <button className="btn btn-primary" onClick={addHolding}>
          Adicionar
        </button>
      </div>

      <div className="holdings-toolbar">
        {quoteError && <p className="error compact">{quoteError}</p>}
        <div className="toolbar-actions">
          <button
            className="btn btn-tertiary"
            onClick={handleRefreshAll}
            disabled={bulkLoading || holdings.length === 0}
            type="button"
          >
            {bulkLoading ? 'Atualizando...' : 'Atualizar tudo'}
          </button>
        </div>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Ativo</th>
              <th>Qtd</th>
              <th>Valor investido</th>
              <th>Ult. Preço</th>
              <th>Valor de mercado</th>
              <th>%</th>
              <th>Compra</th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {holdings.length === 0 && (
              <tr>
                <td colSpan={8} className="muted">
                  Nenhum ativo na carteira.
                </td>
              </tr>
            )}
            {holdings.map((h) => {
              const info = getQuoteInfo(h);
              const effectivePrice =
                info.price ?? (typeof h.last_price === 'number' ? h.last_price : null);
              const invested = h.avg_price * h.quantity;
              const valorCalculado =
                effectivePrice != null ? effectivePrice * h.quantity : h.valor;
              const chipClass = `quote-chip ${info.isFresh ? 'fresh' : 'stale'}`;
              const chipLabel = `Atualizado ha ${formatAgeLabel(info.ageMinutes)}`;
              let priceDisplay: React.ReactNode = '-';
              const displayCurrency = info.currency ?? h.currency;
              const displayOriginal =
                typeof info.price_original === 'number' ? info.price_original : h.last_price_original;
              if (info.loading) {
                priceDisplay = 'Atualizando...';
              } else if (effectivePrice != null) {
                const brl = currencyFormatter.format(effectivePrice);
                if (displayCurrency && displayCurrency !== 'BRL' && typeof displayOriginal === 'number') {
                  const origFmt = new Intl.NumberFormat('pt-BR', {
                    style: 'currency',
                    currency: displayCurrency as Intl.NumberFormatOptions['currency'],
                  });
                  priceDisplay = `${origFmt.format(displayOriginal)} -> ${brl}`;
                } else {
                  priceDisplay = brl;
                }
              }

              const isEditing = editing === h.holding_id;
              let editPreview: string | null = null;
              if (isEditing) {
                const nextQty = toNumber(editQty);
                const nextTotal = toNumber(editPrice);
                if (Number.isFinite(nextQty) && Number.isFinite(nextTotal) && nextQty > 0) {
                  const deltaQty = nextQty - h.quantity;
                  if (Math.abs(deltaQty) > 1e-9) {
                    const nextAvg = nextTotal / nextQty;
                    const appliedPrice = deltaQty > 0 ? nextAvg : h.avg_price;
                    const deltaAbs = Math.abs(deltaQty);
                    const deltaTotal = deltaAbs * appliedPrice;
                    const actionLabel = deltaQty > 0 ? 'Compra automática' : 'Venda automática';
                    editPreview = `${actionLabel}: ${formatQuantityValue(deltaAbs)} @ ${currencyFormatter.format(
                      appliedPrice
                    )} (total ${currencyFormatter.format(deltaTotal)})`;
                  }
                }
              }

              return (
                <tr key={h.holding_id}>
                  <td>
                    <strong>{h.symbol}</strong>
                    {h.name && h.name.trim().toUpperCase() !== h.symbol.trim().toUpperCase() && (
                      <>
                        <br />
                        <span className="muted">{h.name}</span>
                      </>
                    )}
                  {h.class && (
                    <>
                      <br />
                      <span className="muted" style={{ fontSize: 12 }}>
                        Classe: {CLASS_LABELS[(h.class || '').toLowerCase()] || h.class}
                      </span>
                    </>
                  )}
                  {h.currency && h.currency !== 'BRL' && (
                    <>
                      <br />
                      <span className="muted" style={{ fontSize: 12 }}>
                        Moeda original: {h.currency}
                      </span>
                    </>
                  )}
                </td>
                  <td>
                    {isEditing ? (
                      <input
                        className="input"
                        inputMode="decimal"
                        value={editQty}
                        onChange={(e) => setEditQty(e.target.value)}
                      />
                    ) : (
                      formatQuantityValue(h.quantity)
                    )}
                  </td>
                  <td>
                    {isEditing ? (
                      <input
                        className="input"
                        inputMode="decimal"
                        value={editPrice}
                        onChange={(e) => setEditPrice(e.target.value)}
                        title="Valor total investido neste lote"
                      />
                    ) : (
                      currencyFormatter.format(invested)
                    )}
                  </td>
                  <td title={QUOTE_TOOLTIP}>
                    <div className="quote-cell">
                      <span>{priceDisplay}</span>
                      <span className={chipClass}>{chipLabel}</span>
                    </div>
                  </td>
                  <td>{currencyFormatter.format(valorCalculado)}</td>
                  <td>{h.pct.toFixed(1)}%</td>
                  <td>{formatDateLabel(h.purchase_date)}</td>
                  <td>
                    {isEditing ? (
                      <div className="actions-row">
                        {editPreview ? <p className="muted small">{editPreview}</p> : null}
                        <button className="btn btn-primary" onClick={() => saveEdit(h.holding_id)}>
                          Salvar
                        </button>
                        <button className="btn btn-tertiary" onClick={() => setEditing(null)}>
                          Cancelar
                        </button>
                      </div>
                    ) : (
                      <div className="actions-row">
                        <button
                          className="btn btn-secondary"
                          onClick={() => handleRowRefresh(h)}
                          disabled={info.loading}
                        >
                          {info.loading ? 'Atualizando...' : 'Atualizar'}
                        </button>
                        <button className="btn btn-secondary" onClick={() => openSellModal(h)}>
                          Vender
                        </button>
                        <button className="btn btn-ghost" onClick={() => startEdit(h)}>
                          Editar
                        </button>
                        <button
                          className="btn btn-danger"
                          onClick={() => deleteHolding(h.holding_id)}
                        >
                          Excluir
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {searchOpen && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h3>Buscar ticker no Yahoo Finance</h3>
              <button className="modal-close" onClick={() => setSearchOpen(false)}>
                x
              </button>
            </div>
            <div className="modal-body">
              <div className="modal-search-row">
                <input
                  className="input"
                  placeholder="PETR, Itau, Ibovespa..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                <button className="btn btn-primary" onClick={handleSearch} disabled={searchLoading}>
                  {searchLoading ? 'Buscando...' : 'Buscar'}
                </button>
              </div>
              {searchError && <p className="error">{searchError}</p>}
              <div className="modal-results">
                {searchResults.length === 0 && !searchLoading && !searchError && (
                  <p className="muted">Digite um termo e clique em buscar.</p>
                )}
                {searchResults
                  .filter((item) => item.symbol)
                  .map((item) => (
                    <button
                      key={item.symbol}
                      className="search-result"
                      onClick={() => applySearchResult(item)}
                      type="button"
                    >
                      <div className="result-symbol">{item.symbol}</div>
                      <div className="result-name">
                        {item.shortname || item.longname || 'Sem nome'}
                      </div>
                      <div className="result-extra">
                        {[item.exchange, item.type].filter(Boolean).join(' - ')}
                      </div>
                    </button>
                  ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {sellTarget && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h3>Registrar venda - {sellTarget.symbol}</h3>
              <button className="modal-close" onClick={() => setSellTarget(null)}>
                x
              </button>
            </div>
            <div className="modal-body">
              <div className="modal-row">
                <label>Quantidade</label>
                <input
                  className="input"
                  inputMode="decimal"
                  value={sellQty}
                  onChange={(e) => setSellQty(e.target.value)}
                  placeholder={`Disponivel: ${sellTarget.quantity.toLocaleString('pt-BR')}`}
                />
              </div>
              <div className="modal-row">
                <label>Valor de venda</label>
                <input
                  className="input"
                  inputMode="decimal"
                  value={sellPrice}
                  onChange={(e) => setSellPrice(e.target.value)}
                  placeholder="Ex: 32,50"
                />
              </div>
              <div className="modal-row">
                <label>Data da venda</label>
                <input
                  className="input"
                  type="date"
                  max={todayStr}
                  value={sellDate}
                  onChange={(e) => setSellDate(e.target.value)}
                />
              </div>
              {sellError && <p className="error">{sellError}</p>}
            </div>
            <div className="modal-footer">
              <button className="btn btn-primary" onClick={handleSell} disabled={sellLoading}>
                {sellLoading ? 'Salvando...' : 'Confirmar venda'}
              </button>
              <button
                className="btn btn-tertiary"
                onClick={() => setSellTarget(null)}
                disabled={sellLoading}
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

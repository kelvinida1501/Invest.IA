import React, { useMemo, useState } from 'react';
import api from '../Api/ApiClient';

type Asset = {
  id: number;
  symbol: string;
  name: string;
  class: string;
  quantity?: number;
  last_price?: number;
};

type Props = {
  assets: Asset[];
  onRefresh: () => void;
};

const formatCurrency = (v: number) =>
  v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 2 });

export default function AssetsList({ assets, onRefresh }: Props) {
  const [symbol, setSymbol] = useState('');
  const [name, setName] = useState('');
  const [cls, setCls] = useState<Asset['class']>('acao');
  const [submitting, setSubmitting] = useState(false);

  const handleAdd = async () => {
    if (!symbol.trim() || !name.trim()) return;
    setSubmitting(true);
    try {
      await api.post('/assets', {
        symbol: symbol.trim().toUpperCase(),
        name: name.trim(),
        class: cls,
      });
      setSymbol('');
      setName('');
      onRefresh();
    } finally {
      setSubmitting(false);
    }
  };

  const totalValue = useMemo(() => {
    if (!assets?.length) return 0;
    return assets.reduce((sum, a) => sum + (a.quantity ?? 1) * (a.last_price ?? 1), 0);
  }, [assets]);

  return (
    <div>
      {/* FORM */}
      <div className="form-row">
        <input
          className="input"
          placeholder="Símbolo (ex: PETR4.SA)"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
        />
        <input
          className="input"
          placeholder="Nome (ex: Petrobras PN)"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <select className="select" value={cls} onChange={(e) => setCls(e.target.value)}>
          <option value="acao">Ação</option>
          <option value="fii">FII</option>
          <option value="etf">ETF</option>
          <option value="cripto">Cripto</option>
          <option value="renda_fixa">Renda Fixa</option>
        </select>
        <button className="btn btn-primary" onClick={handleAdd} disabled={submitting}>
          {submitting ? 'Adicionando...' : 'Adicionar'}
        </button>
      </div>

      {/* TABELA */}
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Nome</th>
              <th>Classe</th>
              <th>Qtd</th>
              <th>Últ. preço</th>
              <th>Total</th>
            </tr>
          </thead>
          <tbody>
            {(!assets || assets.length === 0) && (
              <tr>
                <td colSpan={6} className="muted">Nenhum ativo</td>
              </tr>
            )}
            {assets?.map((a) => {
              const total = (a.quantity ?? 0) * (a.last_price ?? 0);
              return (
                <tr key={a.id}>
                  <td>{a.symbol}</td>
                  <td>{a.name}</td>
                  <td>{a.class}</td>
                  <td>{a.quantity ?? '-'}</td>
                  <td>{a.last_price != null ? formatCurrency(a.last_price) : '-'}</td>
                  <td>{total ? formatCurrency(total) : '-'}</td>
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={5} className="right strong">Total carteira:</td>
              <td className="strong">{formatCurrency(totalValue)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
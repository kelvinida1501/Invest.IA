import React, { useState } from 'react';
import api from '../Api/ApiClient';

type Holding = {
  holding_id: number;
  asset_id: number;
  symbol: string;
  name: string;
  class: string;
  quantity: number;
  avg_price: number;
  last_price?: number;
  valor: number;
  pct: number;
};

type Props = {
  holdings: Holding[];
  onRefresh: () => void;
};

const CLASSES = [
  { value: 'acao', label: 'Ação' },
  { value: 'etf', label: 'ETF' },
  { value: 'fundo', label: 'Fundo' }, // FII ou fundo em geral
  { value: 'cripto', label: 'Cripto' },
];

export default function HoldingsList({ holdings, onRefresh }: Props) {
  const [symbol, setSymbol] = useState('');
  const [quantity, setQuantity] = useState('');
  const [avgPrice, setAvgPrice] = useState('');
  const [klass, setKlass] = useState('acao');

  const [editing, setEditing] = useState<number | null>(null);
  const [editQty, setEditQty] = useState('');
  const [editPrice, setEditPrice] = useState('');
  const [error, setError] = useState<string | null>(null);

  const addHolding = async () => {
    if (!symbol || !quantity || !avgPrice) {
      setError('Preencha todos os campos.');
      return;
    }

    try {
      setError(null);

      // tenta localizar o ativo pelo ticker
      let assetId: number;
      try {
        const res = await api.get(`/assets?symbol=${symbol.toUpperCase()}`);
        assetId = res.data.id;
      } catch {
        // se não existir, cria com a classe escolhida
        const assetRes = await api.post('/assets', {
          symbol: symbol.toUpperCase(),
          name: symbol.toUpperCase(),
          class: klass, // <— importante
        });
        assetId = assetRes.data.id;
      }

      await api.post('/holdings', {
        asset_id: assetId,
        quantity: parseFloat(quantity),
        avg_price: parseFloat(avgPrice),
      });

      setSymbol('');
      setQuantity('');
      setAvgPrice('');
      setKlass('acao');
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
    setEditQty(h.quantity.toString());
    setEditPrice(h.avg_price.toString());
  };

  const saveEdit = async (id: number) => {
    try {
      await api.put(`/holdings/${id}`, {
        quantity: parseFloat(editQty),
        avg_price: parseFloat(editPrice),
      });
      setEditing(null);
      onRefresh();
    } catch (err) {
      console.error('Erro ao atualizar holding:', err);
    }
  };

  return (
    <div>
      {/* Formulário */}
      <div className="form-row" style={{ gap: 8 }}>
        <input
          className="input"
          placeholder="Ticker (ex: PETR4, IVVB11, MXRF11, BTC)"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
        />

        <select
          className="input"
          value={klass}
          onChange={(e) => setKlass(e.target.value)}
          title="Classe do ativo"
        >
          {CLASSES.map(c => (
            <option key={c.value} value={c.value}>{c.label}</option>
          ))}
        </select>

        <input
          className="input"
          placeholder="Quantidade"
          type="number"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
        />
        <input
          className="input"
          placeholder="Preço médio"
          type="number"
          value={avgPrice}
          onChange={(e) => setAvgPrice(e.target.value)}
        />
        <button className="btn btn-primary" onClick={addHolding}>
          Adicionar
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {/* Tabela */}
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th>Ativo</th>
              <th>Qtd</th>
              <th>Preço Médio</th>
              <th>Últ. Preço</th>
              <th>Valor</th>
              <th>%</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {holdings.length === 0 && (
              <tr>
                <td colSpan={7} className="muted">
                  Nenhum ativo na carteira.
                </td>
              </tr>
            )}
            {holdings.map((h) => (
              <tr key={h.holding_id}>
                <td>
                  <strong>{h.symbol}</strong>
                  <br />
                  <span className="muted">{h.name}</span>
                  {h.class && (
                    <>
                      <br />
                      <span className="muted" style={{ fontSize: 12 }}>Classe: {h.class}</span>
                    </>
                  )}
                </td>
                <td>
                  {editing === h.holding_id ? (
                    <input
                      className="input"
                      type="number"
                      value={editQty}
                      onChange={(e) => setEditQty(e.target.value)}
                    />
                  ) : (
                    h.quantity
                  )}
                </td>
                <td>
                  {editing === h.holding_id ? (
                    <input
                      className="input"
                      type="number"
                      value={editPrice}
                      onChange={(e) => setEditPrice(e.target.value)}
                    />
                  ) : (
                    `R$ ${h.avg_price.toFixed(2)}`
                  )}
                </td>
                <td>{h.last_price ? `R$ ${h.last_price.toFixed(2)}` : '-'}</td>
                <td>R$ {h.valor.toFixed(2)}</td>
                <td>{h.pct.toFixed(1)}%</td>
                <td>
                  {editing === h.holding_id ? (
                    <div className="actions-row">
                      <button className="btn btn-primary" onClick={() => saveEdit(h.holding_id)}>
                        Salvar
                      </button>
                      <button className="btn btn-ghost" onClick={() => setEditing(null)}>
                        Cancelar
                      </button>
                    </div>
                  ) : (
                    <div className="actions-row">
                      <button className="btn btn-ghost" onClick={() => startEdit(h)}>
                        Editar
                      </button>
                      <button className="btn btn-danger" onClick={() => deleteHolding(h.holding_id)}>
                        Excluir
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

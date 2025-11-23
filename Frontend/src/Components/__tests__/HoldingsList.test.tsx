import { render, screen } from '@testing-library/react';
import HoldingsList from '../HoldingsList';
import type { PortfolioHolding } from '../../types/portfolio';

const sampleHolding: PortfolioHolding = {
  holding_id: 1,
  asset_id: 1,
  symbol: 'PETR4.SA',
  name: 'Petrobras',
  class: 'acao',
  quantity: 10,
  avg_price: 20,
  valor: 200,
  pct: 50,
  currency: 'BRL',
  last_price: 22,
  last_price_at: new Date().toISOString(),
  purchase_date: '2024-01-02',
};

describe('HoldingsList', () => {
  it('renders holdings rows with symbol and values', () => {
    render(<HoldingsList holdings={[sampleHolding]} onRefresh={() => {}} />);

    expect(screen.getByText('PETR4.SA')).toBeInTheDocument();
    expect(screen.getByText(/Petrobras/)).toBeInTheDocument();
    const moneyCells = screen.getAllByText(/R\$/);
    expect(moneyCells.length).toBeGreaterThan(0);
    expect(screen.getByText(/Editar/)).toBeInTheDocument();
  });
});

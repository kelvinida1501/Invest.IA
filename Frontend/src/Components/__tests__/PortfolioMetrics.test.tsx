import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import PortfolioMetrics from '../PortfolioMetrics';
import type { PortfolioSummary } from '../../types/portfolio';

const buildSummary = (): PortfolioSummary => ({
  invested_total: 10000,
  market_total: 12000,
  pnl_abs: 2000,
  pnl_pct: 12.34,
  pnl_unrealized_abs: 1500,
  pnl_unrealized_pct: 15.5,
  pnl_realized_abs: 500,
  pnl_realized_pct: 5.1,
  day_change_abs: -100,
  day_change_pct: -0.5,
  as_of: new Date().toISOString(),
  base_currency: 'BRL',
  kpis: {
    invested_total: 10000,
    market_total: 12000,
    pnl_abs: 2000,
    pnl_pct: 12.34,
    pnl_unrealized_abs: 1500,
    pnl_unrealized_pct: 15.5,
    pnl_realized_abs: 500,
    pnl_realized_pct: 5.1,
    day_change_abs: -100,
    day_change_pct: -0.5,
    dividends_ytd: 123.45,
  },
  itens: [
    {
      holding_id: 1,
      asset_id: 10,
      symbol: 'ABC',
      name: 'ABC Corp',
      class: 'acao',
      quantity: 10,
      avg_price: 100,
      valor: 1000,
      pct: 10,
    },
    {
      holding_id: 2,
      asset_id: 20,
      symbol: 'XYZ',
      name: 'XYZ Ltda',
      class: 'etf',
      quantity: 20,
      avg_price: 200,
      valor: 4000,
      pct: 40,
    },
  ],
});

describe('PortfolioMetrics', () => {
  it('exibe placeholder quando não há dados', () => {
    render(<PortfolioMetrics summary={null} loading={false} />);
    expect(screen.getByText(/Sem dados de carteira/i)).toBeInTheDocument();
  });

  it('mostra estado de carregamento sem summary', () => {
    render(<PortfolioMetrics summary={null} loading />);
    expect(screen.getByText(/Carregando carteira/i)).toBeInTheDocument();
  });

  it('renderiza os indicadores sem dividendos', () => {
    const summary = buildSummary();

    render(<PortfolioMetrics summary={summary} loading={false} />);

    const investedMetric = screen.getByText(/Investido/i).closest('.metric');
    expect(investedMetric).not.toBeNull();
    expect(within(investedMetric as HTMLElement).getByText(/R\$/)).toBeInTheDocument();

    const pnlMetric = screen.getByText(/P\/L total/i).closest('.metric');
    expect(pnlMetric).not.toBeNull();
    const pnlValue = within(pnlMetric as HTMLElement).getByText(/R\$/);
    expect(pnlValue).toHaveClass('metric-value', 'positive');
    expect(within(pnlMetric as HTMLElement).getByText(/12\.34%/)).toBeInTheDocument();

    const dayChangeMetric = screen.getByText(/Variação do dia/i).closest('.metric');
    expect(dayChangeMetric).not.toBeNull();
    const dayChangeValue = within(dayChangeMetric as HTMLElement).getByText(/R\$/);
    expect(dayChangeValue).toHaveClass('metric-value', 'negative');
    expect(within(dayChangeMetric as HTMLElement).getByText(/-0\.50%/)).toBeInTheDocument();

    const positionsMetric = screen.getByText(/Ativos na carteira/i).closest('.metric');
    expect(positionsMetric).not.toBeNull();
    expect(within(positionsMetric as HTMLElement).getByText('2')).toBeInTheDocument();
    expect(screen.queryByText(/Dividendos YTD/i)).toBeNull();
  });
});

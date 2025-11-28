import { render, screen, waitFor } from '@testing-library/react';
import React, { act } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import PortfolioPage from '../PortfolioPage';

type Ctx = {
  user: null;
  userLoading: boolean;
  portfolio: any;
  portfolioLoading: boolean;
  reloadPortfolio: () => Promise<void>;
};

const contextState: { value: Ctx } = {
  value: {
    user: null,
    userLoading: false,
    portfolio: null,
    portfolioLoading: false,
    reloadPortfolio: () => Promise.resolve(),
  },
};

let lastHoldingsProps: any;
let lastChartProps: any;
let lastTxProps: any;

vi.mock('../AppLayout', () => ({
  useAppLayoutContext: () => contextState.value,
}));

vi.mock('../../Components/HoldingsList', () => {
  const MockHoldings = (props: any) => {
    lastHoldingsProps = props;
    const { onRegisterSearchTrigger } = props;
    React.useEffect(() => {
      onRegisterSearchTrigger?.(() => {});
    }, [onRegisterSearchTrigger]);
    return <div data-testid="holdings-list" />;
  };

  return {
    __esModule: true,
    default: MockHoldings,
  };
});

vi.mock('../../Components/PortfolioEvolutionChart', () => ({
  __esModule: true,
  default: (props: any) => {
    lastChartProps = props;
    return <div data-testid="chart" data-refresh={props.refreshKey} />;
  },
}));

vi.mock('../../Components/TransactionsHistory', () => ({
  __esModule: true,
  default: (props: any) => {
    lastTxProps = props;
    return <div data-testid="tx-history" data-refresh={props.refreshKey} />;
  },
}));

const buildPortfolio = () => ({
  itens: [
    {
      holding_id: 1,
      asset_id: 10,
      symbol: 'AAA',
      name: 'AAA',
      class: 'acao',
      quantity: 1,
      avg_price: 1,
      valor: 1,
      pct: 1,
    },
  ],
});

describe('PortfolioPage', () => {
  beforeEach(() => {
    lastHoldingsProps = null;
    lastChartProps = null;
    lastTxProps = null;
    contextState.value = {
      user: null,
      userLoading: false,
      portfolio: null,
      portfolioLoading: false,
      reloadPortfolio: vi.fn(() => Promise.resolve()),
    };
  });

  it('mostra placeholder quando não há carteira', () => {
    render(<PortfolioPage />);
    expect(screen.getByText(/Sem ativos para exibir/i)).toBeInTheDocument();
    const yahooBtn = screen.getByRole('button', { name: /Buscar no Yahoo/i });
    expect(yahooBtn).toBeDisabled();
  });

  it('renderiza listas, habilita busca e sincroniza refresh', async () => {
    const reloadPortfolio = vi.fn(() => Promise.resolve());
    contextState.value = {
      user: null,
      userLoading: false,
      portfolio: buildPortfolio(),
      portfolioLoading: false,
      reloadPortfolio,
    };

    render(<PortfolioPage />);

    expect(screen.getByTestId('holdings-list')).toBeInTheDocument();
    const yahooBtn = screen.getByRole('button', { name: /Buscar no Yahoo/i });
    await waitFor(() => expect(yahooBtn).not.toBeDisabled());

    expect(lastChartProps?.refreshKey).toBe(0);
    expect(lastTxProps?.refreshKey).toBe(0);

    await act(async () => {
      lastHoldingsProps.onRefresh();
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(reloadPortfolio).toHaveBeenCalledTimes(1);
      expect(lastChartProps?.refreshKey).toBe(1);
      expect(lastTxProps?.refreshKey).toBe(1);
    });

    await act(async () => {
      lastTxProps.onChange();
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(lastChartProps?.refreshKey).toBe(2);
    });
  });
});

/// <reference types="vitest" />
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import RebalancePanel from '../RebalancePanel';

const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
}));

vi.mock('../../Api/ApiClient', () => ({
  __esModule: true,
  default: {
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
  },
}));

const sampleData = {
  profile: 'moderado',
  profile_source: 'default',
  score: 60,
  total_value: 1000,
  total_value_after: 1100,
  targets: { acao: 0.5, etf: 0.5 },
  bands: { acao: 0.05, etf: 0.05 },
  classes: {
    acao: {
      label: 'Ações',
      current_value: 500,
      current_pct: 0.5,
      target_pct: 0.5,
      floor_pct: 0.45,
      ceiling_pct: 0.55,
      delta_value: 0,
      post_value: 500,
      post_pct: 0.5,
      delta_pct: 0,
    },
  },
  suggestions: [
    {
      symbol: 'ITUB4',
      class: 'acao',
      action: 'comprar',
      quantity: 1,
      value: 10,
      price_ref: 10,
      weight_before: 0.5,
      weight_after: 0.6,
      class_weight_before: 0.5,
      class_weight_after: 0.6,
      rationale: 'teste',
    },
  ],
  within_bands: false,
  turnover: 0.1,
  net_cash_flow: 100,
  rules_applied: ['cap_moderado_por_tolerancia'],
  notes: ['observacao'],
  as_of: '2024-01-01T10:00:00Z',
  candidates: {
    acao: [{ symbol: 'BOVA11', class: 'acao', class_label: 'Ações', description: 'ETF' }],
  },
  options: {
    allow_sells: true,
    prefer_etfs: false,
    min_trade_value: 100,
    max_turnover: 0.25,
  },
};

describe('RebalancePanel', () => {
  beforeEach(() => {
    mockGet.mockReset();
    mockPost.mockReset();
    mockGet.mockResolvedValue({ data: sampleData });
  });

  it('renders summary and suggestions from API payload', async () => {
    render(<RebalancePanel />);

    await waitFor(() => expect(mockGet).toHaveBeenCalled());

    expect(screen.getAllByText(/Turnover/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/ITUB4/)).toBeInTheDocument();
    expect(screen.getByText(/Fluxo/)).toBeInTheDocument();
    expect(screen.getByText(/Sugest/i)).toBeInTheDocument();
  });

  it('shows error when request fails', async () => {
    mockGet.mockRejectedValueOnce(new Error('fail'));

    render(<RebalancePanel />);

    await waitFor(() => expect(screen.getByText(/fail/i)).toBeInTheDocument());
  });
});

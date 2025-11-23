/// <reference types="vitest" />
import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import NewsList from '../NewsList';

const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}));

vi.mock('../../Api/ApiClient', () => ({
  __esModule: true,
  default: { get: mockGet },
}));

describe('NewsList', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it('shows empty state when user has no holdings', async () => {
    mockGet.mockResolvedValue({
      data: { symbols: [], items: [] },
    });

    render(<NewsList />);

    await waitFor(() => expect(mockGet).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/Adicione ativos/i)).toBeInTheDocument();
  });

  it('shows an error message when the request fails', async () => {
    mockGet.mockRejectedValue(new Error('boom'));

    render(<NewsList />);

    await waitFor(() =>
      expect(screen.getByText(/carregar as/i)).toBeInTheDocument()
    );
  });

  it('renders news items with sentiment and tickers', async () => {
    mockGet.mockResolvedValue({
      data: {
        symbols: ['PETR4.SA'],
        items: [
          {
            id: '1',
            headline: 'Petrobras em alta',
            url: 'https://example.com/petr4',
            source: 'Reuters',
            published_at: null,
            sentiment: { label: 'positivo', score: 0.8 },
            tickers: ['PETR4.SA'],
          },
        ],
      },
    });

    render(<NewsList />);

    await waitFor(() =>
      expect(screen.getByText('Petrobras em alta')).toBeInTheDocument()
    );
    expect(screen.getByText(/Positivo/i)).toBeInTheDocument();
    expect(screen.getByText(/PETR4/)).toBeInTheDocument();
    expect(screen.getByText(/Sem data/i)).toBeInTheDocument();
  });
});

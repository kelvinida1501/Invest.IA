import { render, screen } from '@testing-library/react';
import UpdateBadge from '../UpdateBadge';

describe('UpdateBadge', () => {
  it('shows fallback when no date', () => {
    render(<UpdateBadge asOf={null} />);
    expect(screen.getByText(/Sem atualiza/)).toBeInTheDocument();
  });

  it('shows loading text when loading', () => {
    render(<UpdateBadge asOf={null} loading />);
    expect(screen.getByText(/Atualizando/)).toBeInTheDocument();
  });

  it('formats recent datetime', () => {
    const now = new Date().toISOString();
    render(<UpdateBadge asOf={now} />);
    expect(screen.getByText(/Atualizado/)).toBeInTheDocument();
  });
});

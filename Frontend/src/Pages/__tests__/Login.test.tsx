/// <reference types="vitest" />
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Login from '../Login';

const { mockLogin, mockRegister, mockNavigate } = vi.hoisted(() => ({
  mockLogin: vi.fn(),
  mockRegister: vi.fn(),
  mockNavigate: vi.fn(),
}));

vi.mock('../../Api/ApiClient', () => ({
  __esModule: true,
  AuthApi: {
    login: (...args: any[]) => mockLogin(...args),
    register: (...args: any[]) => mockRegister(...args),
  },
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom'
  );
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Login page', () => {
  beforeEach(() => {
    mockLogin.mockReset();
    mockRegister.mockReset();
    mockNavigate.mockReset();
  });

  it('allows switching to register mode and shows extra fields', async () => {
    render(<Login />);
    const user = userEvent.setup();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /Registrar/i }));
    });

    await waitFor(() => {
      expect(screen.getByLabelText(/Nome/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Confirmar senha/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Criar conta/i })).toBeInTheDocument();
    });
  });

  it('navigates to /inicio on successful login', async () => {
    mockLogin.mockResolvedValue({});
    render(<Login />);
    const user = userEvent.setup();

    const submit = screen
      .getAllByRole('button', { name: /Entrar/i })
      .find((btn) => btn.getAttribute('type') === 'submit')!;
    await act(async () => {
      await user.click(submit);
    });

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith('/inicio', { replace: true })
    );
  });

  it('shows error message when login fails', async () => {
    mockLogin.mockRejectedValue({ response: { data: { detail: 'Credenciais' } } });
    render(<Login />);
    const user = userEvent.setup();

    const submit = screen
      .getAllByRole('button', { name: /Entrar/i })
      .find((btn) => btn.getAttribute('type') === 'submit')!;
    await act(async () => {
      await user.click(submit);
    });

    await waitFor(() =>
      expect(screen.getByText(/Credenciais/i)).toBeInTheDocument()
    );
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});

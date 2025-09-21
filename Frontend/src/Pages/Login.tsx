import React, { useEffect, useMemo, useState } from 'react';
import { AuthApi } from '../Api/ApiClient';
import { useNavigate } from 'react-router-dom';
import LogoFull from '../Assets/LogoFull.svg';

type Mode = 'login' | 'register';

export default function Login() {
  const navigate = useNavigate();

  const [mode, setMode] = useState<Mode>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('user@example.com');
  const [password, setPassword] = useState('password');
  const [confirm, setConfirm] = useState('');
  const [showPass, setShowPass] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEmailValid = useMemo(() => /\S+@\S+\.\S+/.test(email), [email]);
  const isPasswordOk = useMemo(() => password.trim().length >= 6, [password]);
  const isConfirmOk = useMemo(
    () => mode === 'login' || password === confirm,
    [mode, password, confirm]
  );
  const formValid =
    mode === 'login'
      ? isEmailValid && isPasswordOk
      : isEmailValid && isPasswordOk && isConfirmOk && name.trim().length >= 2;

  useEffect(() => {
    setError(null);
  }, [mode, email, password, confirm, name]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formValid || loading) return;

    setLoading(true);
    setError(null);
    try {
      if (mode === 'login') {
        await AuthApi.login(email, password);
      } else {
        await AuthApi.register(name, email, password);
        await AuthApi.login(email, password); // auto login
      }
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        'Ocorreu um erro. Tente novamente.';
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="brand">
          <img src={LogoFull} alt="InvestIA" />
          <h1>InvestIA</h1>
        </div>

        <div className="tabs">
          <button
            type="button"
            className={`tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => setMode('login')}
          >
            Entrar
          </button>
          <button
            type="button"
            className={`tab ${mode === 'register' ? 'active' : ''}`}
            onClick={() => setMode('register')}
          >
            Registrar
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          {mode === 'register' && (
            <>
              <label htmlFor="name">Nome</label>
              <input
                id="name"
                placeholder="Seu nome"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="name"
              />
            </>
          )}

          <label htmlFor="email">Email</label>
          <input
            id="email"
            placeholder="voce@exemplo.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />

          <label htmlFor="password">Senha</label>
          <div className="password-field">
            <input
              id="password"
              type={showPass ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
            <button
              type="button"
              className="ghost"
              onClick={() => setShowPass((s) => !s)}
            >
              {showPass ? 'Ocultar' : 'Mostrar'}
            </button>
          </div>

          {mode === 'register' && (
            <>
              <label htmlFor="confirm">Confirmar senha</label>
              <input
                id="confirm"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
              />
            </>
          )}

          <div className="actions">
            <button
              disabled={loading || !formValid}
              type="submit"
              className="primary"
            >
              {loading
                ? mode === 'login'
                  ? 'Entrando...'
                  : 'Registrando...'
                : mode === 'login'
                ? 'Entrar'
                : 'Criar conta'}
            </button>
          </div>

          {error && <p className="error">{error}</p>}
        </form>
      </div>
    </div>
  );
}

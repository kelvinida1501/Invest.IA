import React, { useEffect, useMemo, useState } from 'react';
import { AuthApi } from '../Api/ApiClient';
import { useNavigate } from 'react-router-dom';

import LogoFull from '../Assets/LogoFull.svg';

type Mode = 'login' | 'register';

export default function Login() {
  const navigate = useNavigate();

  const [mode, setMode] = useState<Mode>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
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

  // se já houver token, pula direto
  useEffect(() => {
    const t = localStorage.getItem('token');
    if (t) navigate('/dashboard', { replace: true });
  }, [navigate]);

  const handleLogin = async () => {
    return await AuthApi.login(email, password);
  };

  const handleRegister = async () => {
    return await AuthApi.register(name, email, password);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formValid) return;

    setLoading(true);
    setError(null);
    try {
      const data =
        mode === 'login' ? await handleLogin() : await handleRegister();

      // se registrou e não veio token, tenta logar em seguida
      let token = (data as any)?.access_token;
      if (mode === 'register' && !token) {
        const after = await AuthApi.login(email, password);
        token = after?.access_token;
      }

      if (!token) {
        throw new Error('Login não retornou access_token');
      }

      // avisa o AppRouter que o token mudou
      window.dispatchEvent(new Event('auth-changed'));

      // redireciona
      navigate('/dashboard', { replace: true });
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.response?.data?.message ||
        err?.message ||
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
          {!isEmailValid && (
            <small className="hint">Informe um email válido.</small>
          )}

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
          {!isPasswordOk && (
            <small className="hint">Mínimo de 6 caracteres.</small>
          )}

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
              {!isConfirmOk && (
                <small className="hint">As senhas não conferem.</small>
              )}
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

          <div className="footer-links">
            <button
              type="button"
              className="link"
              onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
            >
              {mode === 'login'
                ? 'Não tem conta? Registre-se'
                : 'Já tem conta? Entrar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

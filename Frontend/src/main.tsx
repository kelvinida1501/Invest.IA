import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './Pages/Login';
import Dashboard from './Pages/Dashboard';
import './Styles/global.css';
import { setAuthToken } from './Api/ApiClient';

function AppRouter() {
  // Inicializa o header Authorization já no primeiro load
  React.useEffect(() => {
    setAuthToken(localStorage.getItem('token') ?? undefined);
  }, []);

  const [token, setToken] = React.useState<string | null>(() =>
    localStorage.getItem('token')
  );

  React.useEffect(() => {
    const update = () => setToken(localStorage.getItem('token'));
    window.addEventListener('storage', update);         // outra aba
    window.addEventListener('auth-changed', update as any); // mesma aba
    return () => {
      window.removeEventListener('storage', update);
      window.removeEventListener('auth-changed', update as any);
    };
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/dashboard"
          element={token ? <Dashboard /> : <Navigate to="/login" replace />}
        />
        <Route
          path="*"
          element={<Navigate to={token ? '/dashboard' : '/login'} replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

createRoot(document.getElementById('root')!).render(<AppRouter />);

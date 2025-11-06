import React from 'react';
import {
  BrowserRouter,
  Route,
  Routes,
  Navigate,
} from 'react-router-dom';
import Login from './Pages/Login';
import AppLayout from './Pages/AppLayout';
import Dashboard from './Pages/Dashboard';
import PortfolioPage from './Pages/PortfolioPage';
import ProfilePage from './Pages/ProfilePage';
import { setAuthToken } from './Api/ApiClient';

export default function App() {
  const [token, setToken] = React.useState<string | null>(() =>
    localStorage.getItem('token')
  );

  React.useEffect(() => {
    setAuthToken(token ?? undefined);
  }, [token]);

  React.useEffect(() => {
    const update = () => setToken(localStorage.getItem('token'));
    window.addEventListener('storage', update);
    window.addEventListener('auth-changed', update as any);
    return () => {
      window.removeEventListener('storage', update);
      window.removeEventListener('auth-changed', update as any);
    };
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={token ? <Navigate to="/inicio" replace /> : <Login />}
        />
        <Route
          element={token ? <AppLayout /> : <Navigate to="/login" replace />}
        >
          <Route index element={<Navigate to="/inicio" replace />} />
          <Route path="/inicio" element={<Dashboard />} />
          <Route path="/carteira" element={<PortfolioPage />} />
          <Route path="/perfil" element={<ProfilePage />} />
        </Route>
        <Route
          path="*"
          element={<Navigate to={token ? '/inicio' : '/login'} replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

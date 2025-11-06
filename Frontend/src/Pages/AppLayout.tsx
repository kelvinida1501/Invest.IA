import React from 'react';
import { NavLink, Outlet, useLocation, useNavigate, useOutletContext } from 'react-router-dom';
import api, { AuthApi } from '../Api/ApiClient';
import logo from '../Assets/LogoFull.svg';
import ChatWidget from '../Components/ChatWidget';
import { PortfolioSummary } from '../types/portfolio';

type AuthUser = {
  id: number;
  name: string;
  email: string;
};

export type AppLayoutContext = {
  user: AuthUser | null;
  userLoading: boolean;
  portfolio: PortfolioSummary | null;
  portfolioLoading: boolean;
  reloadPortfolio: () => Promise<void>;
};

export function useAppLayoutContext() {
  return useOutletContext<AppLayoutContext>();
}

const NAV_LINKS = [
  { to: '/inicio', label: 'Início' },
  { to: '/carteira', label: 'Carteira' },
  { to: '/perfil', label: 'Perfil' },
];

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = React.useState<AuthUser | null>(null);
  const [userLoading, setUserLoading] = React.useState(true);
  const [portfolio, setPortfolio] = React.useState<PortfolioSummary | null>(null);
  const [portfolioLoading, setPortfolioLoading] = React.useState(true);

  const loadUser = React.useCallback(async () => {
    setUserLoading(true);
    try {
      const { data } = await api.get<AuthUser>('/auth/me');
      setUser(data);
    } catch (err) {
      console.error('Erro ao carregar usuário', err);
      AuthApi.logout();
      navigate('/login', { replace: true });
    } finally {
      setUserLoading(false);
    }
  }, [navigate]);

  const reloadPortfolio = React.useCallback(async () => {
    setPortfolioLoading(true);
    try {
      const { data } = await api.get<PortfolioSummary>('/portfolio/summary');
      setPortfolio(data);
    } catch (err) {
      console.error('Erro ao carregar carteira', err);
    } finally {
      setPortfolioLoading(false);
    }
  }, []);

  React.useEffect(() => {
    loadUser();
    reloadPortfolio();
  }, [loadUser, reloadPortfolio]);

  const handleLogout = () => {
    AuthApi.logout();
    navigate('/login', { replace: true });
  };

  const currentTitle = React.useMemo(() => {
    const found = NAV_LINKS.find((link) => link.to === location.pathname);
    return found?.label ?? 'InvestIA';
  }, [location.pathname]);

  return (
    <>
      <div className="app-shell">
        <aside className="app-sidebar">
          <div className="brand">
            <img src={logo} alt="InvestIA" />
            <h1>InvestIA</h1>
          </div>
          <nav className="app-nav">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        <div className="app-main">
          <header className="app-header">
            <div className="app-header-info">
              <h2>{currentTitle}</h2>
            </div>
            <div className="user-pill">
              {userLoading ? (
                <span>Carregando...</span>
              ) : user ? (
                <>
                  <div className="avatar">
                    {String(user.name || '?').charAt(0).toUpperCase()}
                  </div>
                  <span>
                    {user.name} ({user.email})
                  </span>
                </>
              ) : (
                <span>Sem usuário</span>
              )}
              <button className="btn btn-danger" onClick={handleLogout}>
                Sair
              </button>
            </div>
          </header>

          <main className="app-content">
            <Outlet
              context={{
                user,
                userLoading,
                portfolio,
                portfolioLoading,
                reloadPortfolio,
              }}
            />
          </main>
        </div>
      </div>

      <ChatWidget />
    </>
  );
}

import React, { useEffect, useState } from 'react';
import api, { setAuthToken } from '../Api/ApiClient';
import NewsList from '../Components/NewsList';
import ChatBox from '../Components/Chatbox';
import logo from '../Assets/LogoFull.svg';
import AllocationChart from '../Components/AllocationChart';
import HoldingsList from '../Components/HoldingsList';
import RiskPanel from '../Components/RiskPanel';
import RebalancePanel from '../Components/RebalancePanel';

export default function Dashboard() {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const token = localStorage.getItem('token');
    setAuthToken(token ?? undefined);

    async function load() {
      try {
        const [uRes, pRes] = await Promise.all([
          api.get('/auth/me'),
          api.get('/portfolio/summary'),
        ]);
        setUser(uRes.data);
        setPortfolio(pRes.data);
      } catch (err) {
        console.error('Erro ao carregar dashboard:', err);
      }
    }

    load();
  }, []);

  const refreshPortfolio = async () => {
    try {
      const res = await api.get('/portfolio/summary');
      setPortfolio(res.data);
    } catch (err) {
      console.error('Erro ao atualizar portfolio:', err);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setAuthToken();
    window.location.href = '/login';
  };

  return (
    <div className="page">
      <header className="header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <img src={logo} alt="InvestIA" style={{ height: '40px' }} />
          <h1>InvestIA</h1>
        </div>
        <div className="user-pill">
          {user && (
            <>
              <div className="avatar">{user.name.charAt(0).toUpperCase()}</div>
              <span>
                {user.name} ({user.email})
              </span>
            </>
          )}
          <button className="btn btn-danger" onClick={handleLogout}>
            Sair
          </button>
        </div>
      </header>

      <main className="grid">
        {/* KPIs + Perfil de Risco */}
        {portfolio && (
          <section className="card">
            <div className="card-header">
              <h2>Resumo</h2>
              <button className="btn btn-ghost" onClick={refreshPortfolio}>
                Atualizar
              </button>
            </div>
            <div
              className="kpis"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: 12,
                marginBottom: 12,
              }}
            >
              <Kpi title="Investido" value={`R$ ${portfolio.invested_total.toFixed(2)}`} />
              <Kpi title="Mercado" value={`R$ ${portfolio.market_total.toFixed(2)}`} />
              <Kpi title="P/L" value={`R$ ${portfolio.pnl_abs.toFixed(2)}`} />
              <Kpi title="P/L %" value={`${portfolio.pnl_pct.toFixed(2)}%`} />
            </div>

            {/* Perfil de risco */}
            <RiskPanel />
          </section>
        )}

        {/* Alocação da Carteira */}
        <section className="card">
          <div className="card-header">
            <h2>Alocação da Carteira</h2>
            <button className="btn btn-ghost" onClick={refreshPortfolio}>
              Atualizar
            </button>
          </div>
          {portfolio && <AllocationChart assets={portfolio.itens} />}
          {!portfolio && <p className="muted">Carregando carteira...</p>}
        </section>

        {/* Resumo + CRUD de Ativos */}
        <section className="card">
          <div className="card-header">
            <h2>Resumo da Carteira</h2>
            <button className="btn btn-ghost" onClick={refreshPortfolio}>
              Atualizar
            </button>
          </div>
          {portfolio ? (
            <HoldingsList holdings={portfolio.itens} onRefresh={refreshPortfolio} />
          ) : (
            <p className="muted">Nenhum ativo encontrado.</p>
          )}
        </section>

        {/* Rebalanceamento */}
        <section className="card">
          <div className="card-header">
            <h2>Rebalanceamento</h2>
            <button className="btn btn-ghost" onClick={refreshPortfolio}>
              Atualizar carteira
            </button>
          </div>
          <RebalancePanel />
        </section>

        {/* Notícias */}
        <section className="card">
          <div className="card-header">
            <h2>Notícias recentes</h2>
          </div>
          <NewsList />
        </section>

        {/* Chat */}
        <section className="card full">
          <div className="card-header">
            <h2>Chat (Assistente)</h2>
          </div>
          <ChatBox />
        </section>
      </main>
    </div>
  );
}

function Kpi({ title, value }: { title: string; value: string }) {
  return (
    <div
      style={{
        border: '1px solid #eee',
        borderRadius: 8,
        padding: 12,
        background: '#fff',
      }}
    >
      <div className="muted" style={{ fontSize: 12 }}>
        {title}
      </div>
      <div style={{ fontSize: 18, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

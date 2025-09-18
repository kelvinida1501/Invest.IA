import React, { useEffect, useMemo, useState } from "react";
import api, { setAuthToken } from "../Api/ApiClient";
import AssetsList from "../Components/AssetsList";
import NewsList from "../Components/NewsList";
import ChatBox from "../Components/Chatbox";
import AllocationChart from "../Components/AllocationChart";
import logo from "../Assets/LogoFull.svg";
import { useNavigate } from "react-router-dom";

type User = { id: number; name: string; email: string };
type Asset = {
  id: number;
  symbol: string;
  name: string;
  class: string;
  quantity?: number;
  last_price?: number;
};

export default function Dashboard() {
  const navigate = useNavigate();

  const [user, setUser] = useState<User | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // total e % alocação (exibe em cards/header)
  const totalValue = useMemo(() => {
    if (!assets?.length) return 0;
    return assets.reduce(
      (sum, a) => sum + (a.quantity ?? 1) * (a.last_price ?? 1),
      0
    );
  }, [assets]);

  useEffect(() => {
    const token = localStorage.getItem("token");
    setAuthToken(token ?? null);

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        // CORREÇÃO: endpoint certo é /auth/me
        const [uRes, aRes] = await Promise.all([
          api.get("/auth/me"),
          api.get("/assets"),
        ]);
        setUser(uRes.data);
        setAssets(aRes.data);
      } catch (err: any) {
        const detail =
          err?.response?.data?.detail ||
          err?.message ||
          "Falha ao carregar dados do dashboard.";
        setError(detail);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, []);

  const refreshAssets = async () => {
    try {
      const res = await api.get("/assets");
      setAssets(res.data);
    } catch (err) {
      // Mantém UX silenciosa; se quiser, exiba um toast
      console.error(err);
    }
  };

  const handleLogout = () => {
    setAuthToken(null); // limpa Authorization + localStorage
    window.dispatchEvent(new Event("auth-changed")); // força AppRouter a reavaliar token
    navigate("/login", { replace: true });
  };

  if (loading) {
    return (
      <div className="page">
        <header className="header">
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <img src={logo} alt="InvestIA" style={{ height: 40 }} />
            <h1>InvestIA</h1>
          </div>
          <div />
        </header>

        <main className="grid">
          <section className="card">
            <h2>Carregando dados...</h2>
            <p style={{ color: "#666" }}>
              Buscando sua carteira, usuário e notícias.
            </p>
          </section>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page">
        <header className="header">
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <img src={logo} alt="InvestIA" style={{ height: 40 }} />
            <h1>InvestIA</h1>
          </div>
          <div>
            <button className="btn btn-danger" onClick={handleLogout}>
              Sair
            </button>
          </div>
        </header>

        <main className="grid">
          <section className="card">
            <h2>Algo deu errado</h2>
            <p style={{ color: "#d33" }}>{error}</p>
            <button onClick={() => window.location.reload()}>Tentar novamente</button>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <img src={logo} alt="InvestIA" style={{ height: 40 }} />
          <h1>InvestIA</h1>
        </div>

        <div className="header-right" style={{ display: "flex", gap: 12, alignItems: "center" }}>
          {user && (
            <div className="user-pill" title={user.email}>
              <div className="avatar">{user.name?.[0]?.toUpperCase() ?? "U"}</div>
              <span>Olá, {user.name}</span>
            </div>
          )}
          <button className="btn btn-danger" onClick={handleLogout}>Sair</button>
        </div>
      </header>

      {/* KPIs simples */}
      <section className="kpis">
        <div className="kpi-card">
          <div className="kpi-label">Valor da Carteira</div>
          <div className="kpi-value">
            {totalValue.toLocaleString("pt-BR", {
              style: "currency",
              currency: "BRL",
              maximumFractionDigits: 2,
            })}
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Ativos</div>
          <div className="kpi-value">{assets?.length ?? 0}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Perfil</div>
          <div className="kpi-value">—</div>
          <div className="kpi-hint">Teste virá no onboarding</div>
        </div>
      </section>

      <main className="grid">
        <section className="card">
          <div className="card-header">
            <h2>Alocação da Carteira</h2>
            <button className="btn btn-ghost" onClick={refreshAssets}>
              Atualizar
            </button>
          </div>
          <AllocationChart assets={assets} />
        </section>

        <section className="card">
          <div className="card-header">
            <h2>Ativos</h2>
            <button className="btn btn-ghost" onClick={refreshAssets}>
              Atualizar
            </button>
          </div>
          <AssetsList assets={assets} onRefresh={refreshAssets} />
        </section>

        <section className="card">
          <div className="card-header">
            <h2>Notícias recentes</h2>
          </div>
          <NewsList />
        </section>

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

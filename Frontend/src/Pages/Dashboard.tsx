import React from 'react';
import { useAppLayoutContext } from './AppLayout';
import PortfolioMetrics from '../Components/PortfolioMetrics';
import PortfolioPositionsTable from '../Components/PortfolioPositionsTable';
import AllocationPanel from '../Components/AllocationPanel';
import NewsList from '../Components/NewsList';

export default function Dashboard() {
  const { portfolio, portfolioLoading, reloadPortfolio } = useAppLayoutContext();
  const allocationRefreshKey = React.useMemo(() => {
    if (!portfolio) return 'empty';
    return `${portfolio.as_of ?? 'none'}-${portfolio.market_total}`;
  }, [portfolio]);

  return (
    <div className="dashboard-grid">
      <PortfolioMetrics summary={portfolio} loading={portfolioLoading} />

      <div className="dashboard-row">
        <section className="card limit-rows-4">
          <div className="card-header">
            <div>
              <h2>Resumo da carteira</h2>
              <span className="muted small">
                {portfolio?.itens.length ?? 0} ativos cadastrados
              </span>
            </div>
            <button
              className="btn btn-ghost"
              onClick={reloadPortfolio}
              disabled={portfolioLoading}
            >
              Atualizar
            </button>
          </div>
          <PortfolioPositionsTable
            holdings={portfolio?.itens ?? []}
            loading={portfolioLoading}
            compact
            enableFilters={false}
          />
        </section>

        <section className="card">
          <div className="card-header">
            <h2>Alocação atual</h2>
          </div>
          <AllocationPanel refreshKey={allocationRefreshKey} summary={portfolio} />
        </section>
      </div>

      <section className="card full">
        <div className="card-header">
          <h2>Notícias recentes</h2>
        </div>
        <NewsList />
      </section>
    </div>
  );
}

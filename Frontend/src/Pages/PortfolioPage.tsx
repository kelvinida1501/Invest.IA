import React from 'react';
import HoldingsList from '../Components/HoldingsList';
import PortfolioEvolutionChart from '../Components/PortfolioEvolutionChart';
import TransactionsHistory from '../Components/TransactionsHistory';
import { useAppLayoutContext } from './AppLayout';

export default function PortfolioPage() {
  const { portfolio, reloadPortfolio } = useAppLayoutContext();
  const [txRefreshKey, setTxRefreshKey] = React.useState(0);
  const [tsRefreshKey, setTsRefreshKey] = React.useState(0);
  const [openSearch, setOpenSearch] = React.useState<(() => void) | null>(null);

  const handleRefresh = React.useCallback(() => {
    Promise.resolve(reloadPortfolio()).finally(() => {
      setTxRefreshKey((key) => key + 1);
      setTsRefreshKey((key) => key + 1);
    });
  }, [reloadPortfolio]);

  const handleTransactionsChanged = React.useCallback(() => {
    setTsRefreshKey((key) => key + 1);
    void reloadPortfolio();
  }, [reloadPortfolio]);

  const registerSearchTrigger = React.useCallback((fn: () => void) => {
    setOpenSearch(() => fn);
  }, []);

  return (
    <div className="page-grid">
      <section className="card full">
        <div className="card-header">
          <h2>Evolução da carteira</h2>
        </div>
        <PortfolioEvolutionChart refreshKey={tsRefreshKey} />
      </section>

      <section className="card full">
        <div className="card-header">
          <h2>Gerenciar ativos</h2>
          <button
            className="btn btn-secondary"
            onClick={() => openSearch?.()}
            disabled={!openSearch}
          >
            Buscar no Yahoo
          </button>
        </div>
        {portfolio ? (
          <HoldingsList
            holdings={portfolio.itens}
            onRefresh={handleRefresh}
            onRegisterSearchTrigger={registerSearchTrigger}
          />
        ) : (
          <p className="muted">Sem ativos para exibir.</p>
        )}
      </section>

      <section className="card full">
        <div className="card-header">
          <h2>Histórico de transações</h2>
        </div>
        <TransactionsHistory refreshKey={txRefreshKey} onChange={handleTransactionsChanged} />
      </section>
    </div>
  );
}

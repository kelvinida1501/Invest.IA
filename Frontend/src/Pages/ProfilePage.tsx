import React from 'react';
import RiskPanel from '../Components/RiskPanel';
import RebalancePanel from '../Components/RebalancePanel';

export default function ProfilePage() {
  return (
    <div className="page-grid profile-grid">
      <section className="card full">
        <div className="card-header">
          <h2>Perfil do investidor</h2>
        </div>
        <RiskPanel />
      </section>

      <section className="card full">
        <div className="card-header">
          <h2>Rebalanceamento e sugestões</h2>
        </div>
        <RebalancePanel />
      </section>
    </div>
  );
}

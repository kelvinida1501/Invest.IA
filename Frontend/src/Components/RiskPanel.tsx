import React, { useEffect, useState } from 'react';
import api from '../Api/ApiClient';

type RiskResp = {
  profile: 'conservador' | 'moderado' | 'arrojado' | null;
  score: number | null;
  last_updated?: string;
};

export default function RiskPanel() {
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState<RiskResp | null>(null);
  const [showForm, setShowForm] = useState(false);

  // 5 perguntas (1..5)
  const [q1, setQ1] = useState(3);
  const [q2, setQ2] = useState(3);
  const [q3, setQ3] = useState(3);
  const [q4, setQ4] = useState(3);
  const [q5, setQ5] = useState(3);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get('/risk');
      setProfile(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const save = async () => {
    const body = { q1, q2, q3, q4, q5 };
    const { data } = await api.post('/risk', body);
    setProfile({ profile: data.profile, score: data.score });
    setShowForm(false);
  };

  const badgeColor = (p?: string | null) =>
    p === 'conservador' ? '#1e88e5' : p === 'moderado' ? '#fb8c00' : p === 'arrojado' ? '#43a047' : '#9e9e9e';

  return (
    <div>
      {loading ? (
        <p className="muted">Carregando perfil…</p>
      ) : (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div>
              <div className="muted" style={{ fontSize: 12 }}>Seu perfil</div>
              <div style={{ fontWeight: 700, color: badgeColor(profile?.profile) }}>
                {profile?.profile ?? 'não definido'}
                {profile?.score != null && (
                  <span style={{ marginLeft: 8, fontWeight: 500, color: '#616161' }}>({profile.score} pts)</span>
                )}
              </div>
            </div>
            <button className="btn btn-primary" onClick={() => setShowForm((s) => !s)}>
              {profile?.profile ? 'Alterar perfil' : 'Definir perfil'}
            </button>
          </div>

          {showForm && (
            <div style={{ marginTop: 12, border: '1px solid #eee', borderRadius: 8, padding: 12, background: '#fff' }}>
              <p style={{ marginTop: 0 }}><b>Questionário (1 a 5)</b></p>

              <Question label="Quanto desconforto com perdas temporárias?" value={q1} onChange={setQ1} />
              <Question label="Qual seu horizonte de investimento?" value={q2} onChange={setQ2} />
              <Question label="Quanta volatilidade você tolera?" value={q3} onChange={setQ3} />
              <Question label="Quão estável é sua renda?" value={q4} onChange={setQ4} />
              <Question label="Qual sua experiência com investimentos?" value={q5} onChange={setQ5} />

              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button className="btn btn-primary" onClick={save}>Salvar</button>
                <button className="btn btn-ghost" onClick={() => setShowForm(false)}>Cancelar</button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Question({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: React.Dispatch<React.SetStateAction<number>>;
}) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 160px', alignItems: 'center', gap: 12, marginBottom: 8 }}>
      <span>{label}</span>
      <input
        type="range"
        min={1}
        max={5}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value))}
      />
    </div>
  );
}

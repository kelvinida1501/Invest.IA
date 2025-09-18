import React, { useMemo } from "react";
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

type Asset = {
  id: number;
  symbol: string;
  name?: string;
  class?: string;
  quantity?: number;
  last_price?: number;
};

type Props = { assets: Asset[] };

const COLORS = ["#f0b90b", "#4cafef", "#66bb6a", "#ef5350", "#ab47bc", "#29b6f6", "#ffa726", "#26a69a", "#7e57c2"];

const formatCurrency = (v: number) =>
  v.toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 2 });

export default function AllocationChart({ assets }: Props) {
  const data = useMemo(() => {
    if (!assets?.length) return [];

    const raw = assets.map((a) => ({
      name: a.symbol || "—",
      value: (a.quantity ?? 1) * (a.last_price ?? 1),
    }));

    const total = raw.reduce((s, r) => s + r.value, 0) || 1;

    // ordena desc & marca percent
    const ordered = raw
      .map((r) => ({ ...r, pct: (r.value / total) * 100 }))
      .sort((a, b) => b.value - a.value);

    // agrupa <3% em "Outros"
    const major = ordered.filter((x) => x.pct >= 3);
    const minor = ordered.filter((x) => x.pct < 3);
    const othersValue = minor.reduce((s, r) => s + r.value, 0);

    return othersValue > 0 ? [...major, { name: "Outros", value: othersValue, pct: (othersValue / total) * 100 }] : major;
  }, [assets]);

  if (!assets || assets.length === 0) return <p>Nenhum ativo para exibir.</p>;

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const { name, value, pct } = payload[0]?.payload || {};
    return (
      <div style={{ background: "#fff", border: "1px solid #eee", padding: 8, borderRadius: 6 }}>
        <div><b>{name}</b></div>
        <div>Valor: {formatCurrency(value ?? 0)}</div>
        <div>Alocação: {pct ? pct.toFixed(2) : "0"}%</div>
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={110} label>
          {data.map((_, idx) => (
            <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

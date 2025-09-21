import React from 'react';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

type Holding = {
  holding_id: number;
  symbol: string;
  valor: number;
};

type Props = {
  assets: Holding[];
};

const COLORS = ['#f2b705', '#4cafef', '#66bb6a', '#ef5350', '#ab47bc', '#29b6f6', '#8d6e63'];

export default function AllocationChart({ assets }: Props) {
  if (!assets || assets.length === 0) {
    return <p className="muted">Nenhum ativo para exibir.</p>;
  }

  const data = assets.map((h) => ({
    name: h.symbol,
    value: h.valor,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          outerRadius={110}
          label={(props: any) =>
            `${props.name} ${(((props.percent ?? 0) as number) * 100).toFixed(1)}%`
          }
        >
          {data.map((_, idx) => (
            <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(v: number) => `R$ ${v.toFixed(2)}`} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

import React from 'react';
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  Treemap,
} from 'recharts';

type AllocationDatum = {
  key: string;
  label: string;
  value: number;
  weight_pct: number;
  class?: string;
  color?: string;
};

type Props = {
  data: AllocationDatum[];
  mode: 'class' | 'asset';
  height?: number;
};

const PALETTE = [
  '#f2b705',
  '#4cafef',
  '#66bb6a',
  '#ef5350',
  '#ab47bc',
  '#29b6f6',
  '#8d6e63',
  '#ff7043',
  '#26c6da',
  '#ffa726',
  '#9575cd',
  '#26a69a',
  '#ec407a',
];

const CLASS_COLORS: Record<string, string> = {
  acao: '#4cafef',
  etf: '#26c6da',
  fii: '#9575cd',
  fundo: '#9575cd',
  cripto: '#f2b705',
  renda_fixa: '#66bb6a',
  caixa: '#8d6e63',
  outros: '#b0bec5',
};

function getColorFor(item: AllocationDatum, index: number): string {
  if (item.color) return item.color;
  if (item.class && CLASS_COLORS[item.class]) return CLASS_COLORS[item.class];
  return PALETTE[index % PALETTE.length];
}

function formatCurrency(value: number) {
  return value.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 2,
  });
}

function formatPercent(value: number) {
  return `${value.toFixed(2)}%`;
}

type TreemapNode = {
  name: string;
  size: number;
  weight_pct: number;
  value: number;
  fill: string;
};

function buildTreemapData(data: AllocationDatum[]): TreemapNode[] {
  return data.map((item, index) => ({
    name: item.label,
    size: item.value,
    weight_pct: item.weight_pct,
    value: item.value,
    fill: getColorFor(item, index),
  }));
}

const CustomTreemapTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const node = payload[0].payload as TreemapNode;
  return (
    <div className="tooltip-card">
      <div className="tooltip-title">{node.name}</div>
      <div className="tooltip-row">
        <span>Valor</span>
        <strong>{formatCurrency(node.value)}</strong>
      </div>
      <div className="tooltip-row">
        <span>Participacao</span>
        <strong>{formatPercent(node.weight_pct)}</strong>
      </div>
    </div>
  );
};

const CustomPieTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.length) return null;
  const entry = payload[0];
  const datum = entry.payload as AllocationDatum;
  return (
    <div className="tooltip-card">
      <div className="tooltip-title">{datum.label}</div>
      <div className="tooltip-row">
        <span>Valor</span>
        <strong>{formatCurrency(datum.value)}</strong>
      </div>
      <div className="tooltip-row">
        <span>Participacao</span>
        <strong>{formatPercent(datum.weight_pct)}</strong>
      </div>
    </div>
  );
};

export default function AllocationChart({ data, mode, height = 320 }: Props) {
  if (!data || data.length === 0) {
    return <p className="muted">Nenhum dado para exibir.</p>;
  }

  if (mode === 'asset') {
    const treemapData = buildTreemapData(data);
    return (
      <ResponsiveContainer width="100%" height={height}>
        <Treemap data={treemapData} dataKey="size" stroke="#202225" fill="#8884d8">
          <Tooltip content={<CustomTreemapTooltip />} />
        </Treemap>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="label"
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={110}
          label={({ name, percent }) =>
            `${name} ${(((percent ?? 0) as number) * 100).toFixed(1)}%`
          }
        >
          {data.map((item, idx) => (
            <Cell key={item.key} fill={getColorFor(item, idx)} />
          ))}
        </Pie>
        <Tooltip content={<CustomPieTooltip />} />
        <Legend
          verticalAlign="bottom"
          align="center"
          wrapperStyle={{ paddingTop: 12 }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

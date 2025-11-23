export type PortfolioHolding = {
  holding_id: number;
  asset_id: number;
  symbol: string;
  name: string;
  class: string;
  class_original?: string | null;
  quantity: number;
  avg_price: number;
  currency?: string;
  last_price?: number;
  last_price_original?: number;
  last_price_at?: string | null;
  fx_rate?: number | null;
  prev_price?: number;
  prev_price_original?: number;
  prev_price_at?: string | null;
  valor: number;
  valor_prev?: number;
  pct: number;
  pnl_abs?: number;
  pnl_pct?: number;
  day_change_abs?: number;
  day_change_pct?: number;
  created_at?: string | null;
  updated_at?: string | null;
  purchase_date?: string | null;
};

export type PortfolioKpis = {
  invested_total: number;
  market_total: number;
  pnl_abs: number;
  pnl_pct: number;
  pnl_unrealized_abs: number;
  pnl_unrealized_pct: number;
  pnl_realized_abs: number;
  pnl_realized_pct: number;
  day_change_abs: number;
  day_change_pct: number;
  dividends_ytd: number;
};

export type PortfolioSummary = {
  total?: number;
  invested_total: number;
  market_total: number;
  pnl_abs: number;
  pnl_pct: number;
  pnl_unrealized_abs: number;
  pnl_unrealized_pct: number;
  pnl_realized_abs: number;
  pnl_realized_pct: number;
  day_change_abs: number;
  day_change_pct: number;
  as_of: string | null;
  base_currency: string;
  kpis: PortfolioKpis;
  itens: PortfolioHolding[];
  fx_rates?: Record<
    string,
    {
      pair: string;
      rate: number;
      retrieved_at?: string | null;
    }
  >;
};

export type AllocationClassItem = {
  class: string;
  value: number;
  weight_pct: number;
};

export type AllocationAssetItem = {
  holding_id: number | null;
  symbol: string;
  name: string;
  class: string;
  value: number;
  weight_pct: number;
};

export type AllocationResponse = {
  mode: 'class' | 'asset';
  total: number;
  as_of: string | null;
  base_currency: string;
  available_classes: string[];
  applied_class?: string | null;
  group_small: number;
  items: AllocationClassItem[] | AllocationAssetItem[];
};

export type PortfolioTimeseriesPoint = {
  date: string;
  market_value: number;
  invested: number;
  pnl: number;
  pnl_total: number;
  pnl_realized: number;
  pnl_unrealized: number;
};

export type PortfolioTimeseries = {
  as_of: string | null;
  base_currency: string;
  earliest_date: string | null;
  range: string;
  start_date: string | null;
  series: PortfolioTimeseriesPoint[];
};

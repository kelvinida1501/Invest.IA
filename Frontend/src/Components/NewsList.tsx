import React, { useEffect, useMemo, useState } from 'react';
import api from '../Api/ApiClient';

type Sentiment = {
  label: 'positivo' | 'negativo' | 'neutro' | string;
  score?: number;
  magnitude?: number;
};

type NewsItem = {
  id: string;
  headline: string;
  summary?: string | null;
  url: string;
  source?: string | null;
  published_at?: string | null;
  image_url?: string | null;
  tickers?: string[];
  matched_symbols?: string[];
  primary_symbol?: string;
  sentiment?: Sentiment;
  score?: number;
};

type NewsResponse = {
  symbols: string[];
  items: NewsItem[];
  meta?: {
    limit: number;
    per_symbol_limit: number;
    lookback_hours: number;
    order?: string;
    debug?: {
      raw_per_symbol?: Record<string, number>;
      after_cutoff?: Record<string, number>;
    };
  };
};

const MAX_NEWS_TOTAL = 12;
const MAX_PER_SYMBOL = 3;
const SKELETON_COUNT = 4;

function relativeTime(iso?: string | null) {
  if (!iso) return 'Sem data';
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return 'Sem data';
  const now = new Date();
  const diffMs = now.getTime() - parsed.getTime();
  const diffMinutes = Math.max(0, Math.round(diffMs / 60000));
  if (diffMinutes < 60) {
    return diffMinutes <= 1 ? 'há 1 minuto' : `há ${diffMinutes} minutos`;
  }
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) {
    return diffHours === 1 ? 'há 1 hora' : `há ${diffHours} horas`;
  }
  const diffDays = Math.round(diffHours / 24);
  if (diffDays < 30) {
    return diffDays === 1 ? 'há 1 dia' : `há ${diffDays} dias`;
  }
  return parsed.toLocaleDateString('pt-BR');
}

function mapSentiment(sentiment?: Sentiment) {
  if (!sentiment) {
    return { label: 'Indefinido', tone: 'neutral' as const, score: undefined };
  }
  const normalized = sentiment.label?.toLowerCase() ?? 'neutro';
  if (normalized.includes('positivo')) {
    return { label: 'Positivo', tone: 'positive' as const, score: sentiment.score };
  }
  if (normalized.includes('negativo')) {
    return { label: 'Negativo', tone: 'negative' as const, score: sentiment.score };
  }
  return { label: 'Neutro', tone: 'neutral' as const, score: sentiment.score };
}

// Removido: cálculo de porcentagem do sentimento, não exibido na UI

function makeTickerLabel(ticker: string) {
  return ticker.replace('.SA', '');
}

export default function NewsList() {
  const [data, setData] = useState<NewsResponse | null>(null);
  const [error, setError] = useState<boolean>(false);

  useEffect(() => {
    let alive = true;
    setError(false);
    api
      .get<NewsResponse>('/news/portfolio', {
        params: {
          total_limit: MAX_NEWS_TOTAL,
          per_symbol_limit: MAX_PER_SYMBOL,
          lookback_days: 7,
          order: 'recent',
        },
      })
      .then((response) => {
        if (alive) {
          setData(response.data);
        }
      })
      .catch(() => {
        if (alive) {
          setData({ symbols: [], items: [] });
          setError(true);
        }
      });
    return () => {
      alive = false;
    };
  }, []);

  const items = useMemo(() => data?.items ?? [], [data]);
  const hasHoldings = (data?.symbols ?? []).length > 0;

  if (!data) {
    return (
      <div className="news-grid skeleton">
        {Array.from({ length: SKELETON_COUNT }).map((_, index) => (
          <div key={`skeleton-${index}`} className="news-card skeleton">
            <div className="news-card-media">
              <div className="news-card-placeholder" />
            </div>
            <div className="news-card-content">
              <div className="skeleton-line short" />
              <div className="skeleton-line" />
              <div className="skeleton-line" />
              <div className="skeleton-line short" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    if (error) {
      return <p className="muted">Não foi possível carregar as notícias agora. Tente novamente mais tarde.</p>;
    }
    if (!hasHoldings) {
      return <p className="muted">Adicione ativos à sua carteira para receber notícias relacionadas.</p>;
    }
    return <p className="muted">Nenhuma notícia nos últimos 7 dias para os ativos da sua carteira.</p>;
  }

  return (
    <div className="news-grid">
      {items.map((item) => {
        const sentiment = mapSentiment(item.sentiment);
        const timeLabel = relativeTime(item.published_at);
        const fallbackSource = item.source || 'Fonte não informada';
        const summary = item.summary?.trim() ?? '';
        const tickers = item.tickers ?? [];

        return (
          <a
            key={item.id}
            className="news-card"
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            <div className="news-card-media">
              {item.image_url ? (
                <img src={item.image_url} alt="" loading="lazy" />
              ) : (
                <div aria-hidden className="news-card-placeholder" />
              )}
            </div>
            <div className="news-card-content">
              <div className="news-card-header">
                <span className="news-card-source">{fallbackSource}</span>
                <span className="news-card-time">{timeLabel}</span>
              </div>
              <div className={`news-card-sentiment ${sentiment.tone}`}>
                <span>{sentiment.label}</span>
              </div>
              <h3 className="news-card-title">{item.headline}</h3>
              {summary && <p className="news-card-summary">{summary}</p>}
              <div className="news-card-footer">
                <div className="news-card-tickers">
                  {tickers.slice(0, 4).map((ticker) => (
                    <span key={ticker} className="news-card-chip">
                      {makeTickerLabel(ticker)}
                    </span>
                  ))}
                </div>
                <span className="news-card-action">
                  Abrir matéria
                  <span aria-hidden className="news-card-arrow">{'>'}</span>
                </span>
              </div>
            </div>
          </a>
        );
      })}
    </div>
  );
}

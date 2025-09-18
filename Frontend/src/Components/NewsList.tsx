import React, { useEffect, useMemo, useState } from "react";
import api from "../Api/ApiClient";

type News = {
  id: number;
  title: string;
  url: string;
  published_at?: string; // ISO
  sentiment?: "positivo" | "negativo" | "neutro" | string;
};

export default function NewsList() {
  const [news, setNews] = useState<News[] | null>(null);

  useEffect(() => {
    let alive = true;
    api.get("/news").then((r) => {
      if (!alive) return;
      setNews(r.data);
    }).catch(() => setNews([]));
    return () => { alive = false; };
  }, []);

  const items = useMemo(() => {
    if (!news) return [];
    return [...news].sort((a, b) => {
      const da = a.published_at ? Date.parse(a.published_at) : 0;
      const db = b.published_at ? Date.parse(b.published_at) : 0;
      return db - da;
    });
  }, [news]);

  const formatDate = (iso?: string) => {
    if (!iso) return "—";
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString("pt-BR");
  };

  const Sentiment = ({ s }: { s?: string }) => {
    const norm = (s || "—").toLowerCase();
    const color =
      norm.includes("positivo") ? "#2e7d32" :
      norm.includes("negativo") ? "#c62828" :
      "#616161";
    return (
      <span style={{ color, fontWeight: 600 }}>
        {s ?? "—"}
      </span>
    );
  };

  if (news === null) {
    // skeleton loader
    return (
      <div>
        {[...Array(4)].map((_, i) => (
          <div key={i} style={{ marginBottom: 10 }}>
            <div style={{ height: 12, background: "#eee", width: "80%", borderRadius: 6 }} />
            <div style={{ height: 10, background: "#f3f3f3", width: "40%", marginTop: 6, borderRadius: 6 }} />
          </div>
        ))}
      </div>
    );
  }

  if (items.length === 0) {
    return <p>Nenhuma notícia no momento.</p>;
  }

  return (
    <div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {items.map((n) => (
          <li key={n.id} style={{ marginBottom: 10 }}>
            <a href={n.url} target="_blank" rel="noreferrer" style={{ fontWeight: 600 }}>
              {n.title}
            </a>
            <div style={{ fontSize: 12, color: "#666" }}>
              {formatDate(n.published_at)} — impacto: <Sentiment s={n.sentiment} />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

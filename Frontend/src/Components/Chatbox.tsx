import React, { useEffect, useRef, useState } from "react";
import api from "../Api/ApiClient";

type Msg = { from: "user" | "bot"; text: string };

const STORAGE_KEY = "chat_history";

export default function ChatBox() {
  const [msg, setMsg] = useState("");
  const [history, setHistory] = useState<Msg[]>(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as Msg[]) : [];
    } catch {
      return [];
    }
  });
  const [loading, setLoading] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
    // scroll bottom
    const el = boxRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [history]);

  const send = async () => {
    const userMsg = msg.trim();
    if (!userMsg || loading) return;

    setHistory((h) => [...h, { from: "user", text: userMsg }]);
    setMsg("");
    setLoading(true);

    try {
      const res = await api.post("/chat", { message: userMsg });
      setHistory((h) => [...h, { from: "bot", text: res.data?.reply ?? "Sem resposta." }]);
    } catch (err) {
      setHistory((h) => [...h, { from: "bot", text: "Erro ao consultar o assistente." }]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setHistory([]);
    localStorage.removeItem(STORAGE_KEY);
  };

  return (
    <div>
      <div
        ref={boxRef}
        style={{ height: 240, overflow: "auto", border: "1px solid #eee", borderRadius: 8, padding: 8, background: "#fff" }}
      >
        {history.map((h, i) => (
          <div key={i} style={{ textAlign: h.from === "user" ? "right" : "left", marginBottom: 6 }}>
            <b>{h.from === "user" ? "Você" : "Assistente"}</b>: {h.text}
          </div>
        ))}
        {loading && (
          <div style={{ textAlign: "left", color: "#666", fontStyle: "italic" }}>
            Assistente está digitando…
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <input
          style={{ flex: 1 }}
          value={msg}
          onChange={(e) => setMsg(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Pergunte sobre sua carteira, notícias, etc."
        />
        <button onClick={send} disabled={loading || !msg.trim()}>
          {loading ? "..." : "Enviar"}
        </button>
        <button className="ghost" onClick={clearChat} disabled={loading}>
          Limpar
        </button>
      </div>
    </div>
  );
}

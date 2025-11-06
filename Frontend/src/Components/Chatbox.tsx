import React, { useEffect, useRef, useState } from 'react';
import api from '../Api/ApiClient';

type Msg = { from: 'user' | 'bot'; text: string };

const STORAGE_KEY = 'chat_history';

export default function ChatBox() {
  const [msg, setMsg] = useState('');
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
    const el = boxRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [history]);

  const send = async () => {
    const userMsg = msg.trim();
    if (!userMsg || loading) return;

    setHistory((prev) => [...prev, { from: 'user', text: userMsg }]);
    setMsg('');
    setLoading(true);

    try {
      const res = await api.post('/chat', { message: userMsg });
      setHistory((prev) => [
        ...prev,
        { from: 'bot', text: res.data?.reply ?? 'Sem resposta.' },
      ]);
    } catch (err) {
      console.error(err);
      setHistory((prev) => [
        ...prev,
        { from: 'bot', text: 'Erro ao consultar o assistente.' },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setHistory([]);
    localStorage.removeItem(STORAGE_KEY);
  };

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    void send();
  };

  return (
    <form className="chatbox" onSubmit={handleSubmit}>
      <div ref={boxRef} className="chat-history">
        {history.length === 0 && !loading ? (
          <p className="chat-placeholder muted small">
            Nenhuma conversa ainda. Envie uma mensagem para começar.
          </p>
        ) : null}

        {history.map((message, index) => (
          <div key={index} className={`chat-message ${message.from}`}>
            <span className="chat-author muted small">
              {message.from === 'user' ? 'Você' : 'Assistente'}
            </span>
            <div className="chat-bubble">{message.text}</div>
          </div>
        ))}

        {loading && (
          <div className="chat-message bot">
            <span className="chat-author muted small">Assistente</span>
            <div className="chat-bubble typing">Digitando…</div>
          </div>
        )}
      </div>

      <div className="chat-composer">
        <input
          className="input chat-input"
          value={msg}
          onChange={(event) => setMsg(event.target.value)}
          placeholder="Pergunte sobre sua carteira, notícias, etc."
          aria-label="Mensagem para o assistente"
          disabled={loading}
        />
        <div className="chat-actions">
          <button type="submit" className="btn btn-primary" disabled={loading || !msg.trim()}>
            {loading ? 'Enviando…' : 'Enviar'}
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={clearChat}
            disabled={loading || history.length === 0}
          >
            Limpar
          </button>
        </div>
      </div>
    </form>
  );
}

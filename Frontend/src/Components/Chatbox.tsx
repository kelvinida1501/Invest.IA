import React, { useEffect, useRef, useState } from 'react';
import api from '../Api/ApiClient';

type Msg = { from: 'user' | 'bot'; text: string };

type ChatResponse = {
  reply?: string;
  session_id?: number;
  used_fallback?: boolean;
};

const HISTORY_KEY = 'chat_history';
const SESSION_KEY = 'chat_session_id';

const readHistory = (): Msg[] => {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    return raw ? (JSON.parse(raw) as Msg[]) : [];
  } catch {
    return [];
  }
};

const readSession = (): number | null => {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(SESSION_KEY);
    const parsed = raw ? Number(raw) : NaN;
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  } catch {
    return null;
  }
};

export default function ChatBox() {
  const [msg, setMsg] = useState('');
  const [history, setHistory] = useState<Msg[]>(readHistory);
  const [sessionId, setSessionId] = useState<number | null>(readSession);
  const [loading, setLoading] = useState(false);
  const [fallbackActive, setFallbackActive] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
    } catch {
      /* ignore */
    }
    const el = boxRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [history]);

  const persistSession = (id: number | null) => {
    if (typeof window === 'undefined') return;
    try {
      if (id) {
        window.localStorage.setItem(SESSION_KEY, String(id));
      } else {
        window.localStorage.removeItem(SESSION_KEY);
      }
    } catch {
      /* ignore */
    }
  };

  const createSession = async (): Promise<number | null> => {
    try {
      const { data } = await api.post('/chat/session');
      const newId = data?.session_id;
      if (typeof newId === 'number' && newId > 0) {
        persistSession(newId);
        setSessionId(newId);
        return newId;
      }
    } catch (err) {
      console.error('Falha ao criar sessao do chat', err);
    }
    return null;
  };

  const ensureSession = async (): Promise<number | null> => {
    if (sessionId) {
      return sessionId;
    }
    return createSession();
  };

  const send = async () => {
    const userMsg = msg.trim();
    if (!userMsg || loading) return;

    setHistory((prev) => [...prev, { from: 'user', text: userMsg }]);
    setMsg('');
    setLoading(true);

    const activeSession = await ensureSession();
    if (!activeSession) {
      setLoading(false);
      setHistory((prev) => [
        ...prev,
        { from: 'bot', text: 'Nao foi possivel iniciar o chat agora.' },
      ]);
      return;
    }

    try {
      const res = await api.post('/chat', { message: userMsg, session_id: activeSession });
      const payload: ChatResponse = res.data ?? {};
      if (payload.session_id && payload.session_id !== sessionId) {
        persistSession(payload.session_id);
        setSessionId(payload.session_id);
      }
      setFallbackActive(Boolean(payload.used_fallback));
      setHistory((prev) => [
        ...prev,
        { from: 'bot', text: payload.reply ?? 'Sem resposta.' },
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
    setFallbackActive(false);
    setSessionId(null);
    try {
      window.localStorage.removeItem(HISTORY_KEY);
    } catch {
      /* ignore */
    }
    persistSession(null);
    void createSession();
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
            Nenhuma conversa ainda. Envie uma mensagem para comecar.
          </p>
        ) : null}

        {history.map((message, index) => (
          <div key={index} className={`chat-message ${message.from}`}>
            <span className="chat-author muted small">
              {message.from === 'user' ? 'Voce' : 'Assistente'}
            </span>
            <div className="chat-bubble">{message.text}</div>
          </div>
        ))}

        {loading && (
          <div className="chat-message bot">
            <span className="chat-author muted small">Assistente</span>
            <div className="chat-bubble typing">Digitando...</div>
          </div>
        )}
      </div>

      {fallbackActive ? (
        <div className="chat-alert warning small">
          Assistente de IA temporariamente offline. Resposta baseada nos dados locais.
        </div>
      ) : null}

      <div className="chat-composer">
        <input
          className="input chat-input"
          value={msg}
          onChange={(event) => setMsg(event.target.value)}
          placeholder="Pergunte sobre sua carteira, noticias, etc."
          aria-label="Mensagem para o assistente"
          disabled={loading}
        />
        <div className="chat-actions">
          <button type="submit" className="btn btn-primary" disabled={loading || !msg.trim()}>
            {loading ? 'Enviando...' : 'Enviar'}
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

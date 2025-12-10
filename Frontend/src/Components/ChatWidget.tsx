import React from 'react';
import ChatBox from './Chatbox';

type ChatWidgetProps = {
  userId?: number | null;
};

const CLOSE_SYMBOL = 'x';

export default function ChatWidget({ userId = null }: ChatWidgetProps) {
  const [open, setOpen] = React.useState(false);
  const panelRef = React.useRef<HTMLDivElement | null>(null);
  const panelId = React.useId();
  const titleId = React.useId();

  React.useEffect(() => {
    if (!open) return undefined;

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };

    const handleClickOutside = (event: MouseEvent | TouchEvent) => {
      if (!panelRef.current) return;
      if (!panelRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchstart', handleClickOutside);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchstart', handleClickOutside);
    };
  }, [open]);

  const toggle = () => setOpen((prev) => !prev);

  return (
    <div className="chat-widget">
      {open ? (
        <div
          ref={panelRef}
          className="chat-panel"
          role="dialog"
          aria-modal="false"
          id={panelId}
          aria-labelledby={titleId}
        >
          <div className="chat-panel-header">
            <div>
              <span className="chat-panel-title" id={titleId}>
                Assistente 
              </span>
              <span className="chat-panel-subtitle">
                Pergunte sobre sua carteira e mercado.
              </span>
            </div>
            <button
              type="button"
              className="chat-close"
              onClick={() => setOpen(false)}
              aria-label="Fechar chat"
            >
              {CLOSE_SYMBOL}
            </button>
          </div>
          <div className="chat-panel-body">
            <ChatBox userId={userId} />
          </div>
        </div>
      ) : null}

      <button
        type="button"
        className="chat-fab"
        onClick={toggle}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        aria-label={open ? 'Fechar chat' : 'Abrir chat'}
      >
        {open ? (
          CLOSE_SYMBOL
        ) : (
          <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor" aria-hidden="true">
            <path d="M4 4h16a1 1 0 0 1 1 1v11.5a1 1 0 0 1-1.6.8L15 14H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Zm1 10h10.4L18 16.2V6H5v8Zm2-6h8v2H7V8Zm0 3h6v2H7v-2Z" />
          </svg>
        )}
      </button>
    </div>
  );
}

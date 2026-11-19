import React, { useEffect, useState } from 'react';
import { getChatStatus, sendChat } from '../../api/client';

const MAX_HISTORY = 20;

// Floating study assistant. Renders nothing unless the user is signed in and the server has an API key.
export default function ChatWidget({ t, session }) {
  const token = session?.token;
  const [enabled, setEnabled] = useState(false);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) { setEnabled(false); setOpen(false); setMessages([]); return; }
    let active = true;
    getChatStatus(token)
      .then(status => { if (active) setEnabled(Boolean(status.enabled)); })
      .catch(() => { if (active) setEnabled(false); });
    return () => { active = false; };
  }, [token]);

  if (!token || !enabled) return null;

  async function send(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    const next = [...messages, { role: 'user', content: text }];
    setMessages(next);
    setDraft('');
    setBusy(true);
    setError('');
    try {
      const { reply } = await sendChat(next.slice(-MAX_HISTORY), token);
      setMessages([...next, { role: 'assistant', content: reply }]);
    } catch (err) {
      setError(err.message || t('failed'));
    } finally {
      setBusy(false);
    }
  }

  function onKeyDown(event) {
    if (event.key === 'Escape') setOpen(false);
  }

  return <div className="chat-widget" onKeyDown={onKeyDown}>
    {open && <section className="chat-panel" aria-label={t('assistantTitle')}>
      <header className="chat-head">
        <strong>{t('assistantTitle')}</strong>
        <button type="button" className="quiet" onClick={() => setOpen(false)} aria-label={t('assistantClose')}>×</button>
      </header>
      <div className="chat-log" role="log" aria-live="polite">
        {messages.length === 0 && <p className="muted">{t('assistantEmpty')}</p>}
        {messages.map((m, i) => <p key={i} className={m.role === 'user' ? 'chat-msg user' : 'chat-msg bot'}>{m.content}</p>)}
        {busy && <p className="muted">{t('assistantThinking')}</p>}
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <form className="chat-form" onSubmit={send}>
        <label className="visually-hidden" htmlFor="chat-input">{t('assistantPlaceholder')}</label>
        <input id="chat-input" value={draft} onChange={e => setDraft(e.target.value)} maxLength={2000}
          placeholder={t('assistantPlaceholder')} disabled={busy}/>
        <button type="submit" disabled={busy || !draft.trim()}>{t('assistantSend')}</button>
      </form>
    </section>}
    <button type="button" className="chat-fab" aria-expanded={open} onClick={() => setOpen(v => !v)}>
      {t('assistantOpen')}
    </button>
  </div>;
}

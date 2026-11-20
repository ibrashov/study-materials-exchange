import React, { useEffect, useState } from 'react';
import { getChatStatus, sendChat } from '../../api/client';

const MAX_HISTORY = 20;

// Floating AI study assistant agent. Renders nothing unless signed in and server has an API key.
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
      .then(status => {
        if (!active) return;
        setEnabled(Boolean(status.enabled));
      })
      .catch(() => { if (active) setEnabled(false); });
    return () => { active = false; };
  }, [token]);

  if (!token || !enabled) return null;

  async function submitText(text) {
    const clean = text.trim();
    if (!clean || busy) return;
    const next = [...messages, { role: 'user', content: clean }];
    setMessages(next);
    setDraft('');
    setBusy(true);
    setError('');
    try {
      const apiMessages = next.slice(-MAX_HISTORY).map(({ role, content }) => ({ role, content }));
      const data = await sendChat(apiMessages, token);
      setMessages([...next, { role: 'assistant', content: data.reply }]);
    } catch (err) {
      setError(err.message || t('failed'));
    } finally {
      setBusy(false);
    }
  }

  function send(event) {
    event.preventDefault();
    submitText(draft);
  }

  function onKeyDown(event) {
    if (event.key === 'Escape') setOpen(false);
  }

  return <div className="chat-widget" onKeyDown={onKeyDown}>
    {open && <section className="chat-panel" aria-label={t('assistantTitle')}>
      <header className="chat-head">
        <div>
          <strong>{t('assistantTitle')}</strong>
        </div>
        <button type="button" className="quiet" onClick={() => setOpen(false)} aria-label={t('assistantClose')}>×</button>
      </header>
      <div className="chat-log" role="log" aria-live="polite">
        {messages.length === 0 && <div className="chat-empty">
          <p className="muted">{t('assistantEmpty')}</p>
          <div className="chat-suggestions">
            <button type="button" className="chat-chip" onClick={() => submitText(t('assistantPromptMaterials'))}>{t('assistantPromptMaterials')}</button>
            <button type="button" className="chat-chip" onClick={() => submitText(t('assistantPromptProgress'))}>{t('assistantPromptProgress')}</button>
          </div>
        </div>}
        {messages.map((m, i) => <div key={i} className={m.role === 'user' ? 'chat-msg user' : 'chat-msg bot'}>
          <p>{m.content}</p>
        </div>)}
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

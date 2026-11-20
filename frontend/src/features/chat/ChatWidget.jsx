import React, { useEffect, useState } from 'react';
import { getChatAgentInfo, getChatStatus, sendChat } from '../../api/client';

const MAX_HISTORY = 20;

// Floating AI study assistant agent. Renders nothing unless signed in and server has an API key.
export default function ChatWidget({ t, session }) {
  const token = session?.token;
  const [enabled, setEnabled] = useState(false);
  const [agentInfo, setAgentInfo] = useState(null);
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) { setEnabled(false); setAgentInfo(null); setOpen(false); setMessages([]); return; }
    let active = true;
    getChatStatus(token)
      .then(status => {
        if (!active) return;
        const isEnabled = Boolean(status.enabled);
        setEnabled(isEnabled);
        if (isEnabled) {
          getChatAgentInfo(token).then(info => { if (active) setAgentInfo(info); }).catch(() => {});
        }
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
      const data = await sendChat(apiMessages, token, true);
      setMessages([...next, { role: 'assistant', content: data.reply, toolsUsed: data.tools_used || [] }]);
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

  const toolCount = agentInfo?.active_tools?.length || 0;

  return <div className="chat-widget" onKeyDown={onKeyDown}>
    {open && <section className="chat-panel" aria-label={t('assistantTitle')}>
      <header className="chat-head">
        <div>
          <strong>{t('assistantTitle')}</strong>
          {toolCount > 0 && <span className="chat-agent-badge">{t('assistantAgentBadge', { count: toolCount })}</span>}
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
          {m.toolsUsed?.length > 0 && <div className="chat-tools-used">
            {Array.from(new Set(m.toolsUsed)).map(tool => <span key={tool} className="chat-tool-pill">{t(`agent.tool.${tool}`)}</span>)}
          </div>}
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

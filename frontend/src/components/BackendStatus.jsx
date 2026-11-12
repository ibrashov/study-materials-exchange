import React from 'react';
import { useEffect, useState } from 'react';
import { getHealth } from '../api/client';

export default function BackendStatus({ t }) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState({ status: 'loading' });
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setState({ status: 'loading' });
    const timeout = setTimeout(() => controller.abort(), 90000);
    getHealth({ signal: controller.signal })
      .then(data => { if (active) setState({ status: 'connected', data }); })
      .catch(error => { if (active) setState({ status: 'error', error }); })
      .finally(() => clearTimeout(timeout));
    return () => { active = false; clearTimeout(timeout); controller.abort(); };
  }, [attempt]);
  return <section className={`connection ${state.status}`} aria-labelledby="connection-title">
    <h2 id="connection-title">{t('connection.title')}</h2>
    <div role="status" aria-live="polite">
      {state.status === 'loading' && <p>{t('connection.loading')}</p>}
      {state.status === 'connected' && <p>{t('connection.connected', state.data)}</p>}
      {state.status === 'error' && <p>{t('connection.failed', { details: state.error.message })}</p>}
    </div>
    <button onClick={() => setAttempt(value => value + 1)} disabled={state.status === 'loading'}>{t('connection.check')}</button>
  </section>;
}

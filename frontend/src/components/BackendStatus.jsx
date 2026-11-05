import React from 'react';
import { useEffect, useState } from 'react';
import { connectionError, getHealth } from '../api/client';

export default function BackendStatus() {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState({ status: 'loading' });
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setState({ status: 'loading' });
    const timeout = setTimeout(() => controller.abort(), 8000);
    getHealth({ signal: controller.signal })
      .then(data => { if (active) setState({ status: 'connected', data }); })
      .catch(error => { if (active) setState({ status: 'error', message: connectionError(error) }); })
      .finally(() => clearTimeout(timeout));
    return () => { active = false; clearTimeout(timeout); controller.abort(); };
  }, [attempt]);
  return <section className={`connection ${state.status}`} aria-labelledby="connection-title">
    <h2 id="connection-title">Backend connection</h2>
    <div role="status" aria-live="polite">
      {state.status === 'loading' && <p>Connecting to FastAPI?</p>}
      {state.status === 'connected' && <p>Connected ? {state.data.service} ? {state.data.status}</p>}
      {state.status === 'error' && <p>{state.message}</p>}
    </div>
    <button onClick={() => setAttempt(value => value + 1)} disabled={state.status === 'loading'}>Check connection</button>
  </section>;
}

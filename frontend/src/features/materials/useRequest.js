import { useCallback, useEffect, useState } from 'react';

const TIMEOUT_MS = 8000;

// Runs an abortable request, ignores stale answers and keeps the last data visible while reloading.
export function useRequest(load, dependencies) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState({ status: 'loading' });
  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setState(previous => ({ status: 'loading', data: previous.data }));
    const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
    load(controller.signal)
      .then(data => { if (active) setState({ status: 'success', data }); })
      .catch(error => { if (active) setState({ status: 'error', error }); })
      .finally(() => clearTimeout(timeout));
    return () => { active = false; clearTimeout(timeout); controller.abort(); };
  }, [...dependencies, attempt]);
  const retry = useCallback(() => setAttempt(value => value + 1), []);
  return { ...state, retry };
}

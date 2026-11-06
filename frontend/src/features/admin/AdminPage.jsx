import React, { useEffect, useState } from 'react';
import { request } from '../../api/client';
import { errorKey } from '../../locales/messages';
export default function AdminPage({ session, t }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!session) return;
    const controller = new AbortController();
    setData(null); setError('');
    request('/admin/overview', { token: session.token, signal: controller.signal }).then(setData)
      .catch(err => { if (!controller.signal.aborted) setError(errorKey(err)); });
    return () => controller.abort();
  }, [session, attempt]);
  return <section><h1>{t('admin')}</h1>{!session ? <p role="alert">{t('denied')}</p> : error ?
    <div role="alert"><p>{t(error)}</p><button onClick={() => setAttempt(v => v + 1)}>{t('retry')}</button></div> : !data ? <p>{t('loading')}</p> :
    <dl className="stats"><div><dt>{t('totalUsers')}</dt><dd>{data.total_users}</dd></div><div><dt>{t('totalMaterials')}</dt><dd>{data.total_materials}</dd></div></dl>}
  </section>;
}

import React from 'react';
import { errorKey } from '../../locales/messages';

// Shows loading and failure for one panel, so one broken report does not hide the others.
export default function AdminPanel({ id, title, request, t, children }) {
  return <section className="admin-panel" aria-labelledby={id}><h2 id={id}>{title}</h2>
    {request.status === 'error' ? <div role="alert"><p>{t(errorKey(request.error))}</p><button onClick={request.retry}>{t('retry')}</button></div>
      : request.data === undefined ? <p>{t('loading')}</p> : children(request.data)}
  </section>;
}

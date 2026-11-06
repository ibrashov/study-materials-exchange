import React, { useState } from 'react';
import { deleteMaterial, downloadMaterial } from '../../api/client';
import { errorKey } from '../../locales/messages';
import { formatFileSize, formatUploadedAt, labelFor } from './format';

export default function MaterialList({ items, categoryNames, courseNames, busy, session, t, onDeleted }) {
  const [working, setWorking] = useState(null);
  const [error, setError] = useState('');
  async function run(id, action) {
    setWorking(id); setError('');
    try { await action(); }
    catch (err) { setError(errorKey(err)); }
    finally { setWorking(null); }
  }
  const canDelete = item => session && (session.user.role === 'admin' || item.uploader_id === session.user.user_id);
  function remove(item) {
    if (!window.confirm(t('materials.deleteConfirm', { title: item.title }))) return;
    run(item.material_id, async () => { await deleteMaterial(item.material_id, session.token); onDeleted(); });
  }
  return <>{error && <p role="alert">{t(error)}</p>}<ul className="materials-list" aria-busy={busy}>
    {items.map(item => <li key={item.material_id} className="materials-item">
      <p className="materials-tag">{labelFor(categoryNames, item.category_id, 'materials.categoryFallback', t)}</p>
      <h2>{item.title}</h2>
      <p>{labelFor(courseNames, item.course_id, 'materials.courseFallback', t)}</p>
      <p className="materials-meta">{formatFileSize(item.file_size_bytes, t)} · {t('materials.uploaded', { date: formatUploadedAt(item.uploaded_at, t) })}</p>
      <div className="materials-item-actions">
        {session ? <button disabled={working !== null} onClick={() => run(item.material_id, () => downloadMaterial(item.material_id, session.token))}>{t(working === item.material_id ? 'loading' : 'download')}</button> : <a href="#login">{t('downloadLogin')}</a>}
        {canDelete(item) && <button disabled={working !== null} onClick={() => remove(item)}>{t('delete')}</button>}
      </div>
    </li>)}
  </ul></>;
}

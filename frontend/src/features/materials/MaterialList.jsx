import React, { useState } from 'react';
import { downloadMaterial } from '../../api/client';
import { errorKey } from '../../locales/messages';
import { formatFileSize, formatUploadedAt, labelFor } from './format';

export default function MaterialList({ items, categoryNames, courseNames, busy, session, t }) {
  const [downloading, setDownloading] = useState(null);
  const [error, setError] = useState('');
  async function download(id) {
    setDownloading(id); setError('');
    try { await downloadMaterial(id, session.token); }
    catch (err) { setError(errorKey(err)); }
    finally { setDownloading(null); }
  }
  return <>{error && <p role="alert">{t(error)}</p>}<ul className="materials-list" aria-busy={busy}>
    {items.map(item => <li key={item.material_id} className="materials-item">
      <p className="materials-tag">{labelFor(categoryNames, item.category_id, 'Category')}</p>
      <h2>{item.title}</h2>
      <p>{labelFor(courseNames, item.course_id, 'Course')}</p>
      <p className="materials-meta">{formatFileSize(item.file_size_bytes)} · Uploaded {formatUploadedAt(item.uploaded_at)}</p>
      {session ? <button disabled={downloading !== null} onClick={() => download(item.material_id)}>{t(downloading === item.material_id ? 'loading' : 'download')}</button> : <a href="#login">{t('downloadLogin')}</a>}
    </li>)}
  </ul></>;
}

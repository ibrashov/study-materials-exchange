import React, { useState } from 'react';
import { deleteMaterial, emptyTrash, getCategories, getCourses, getTrash, restoreMaterial } from '../../api/client';
import { errorKey } from '../../locales/messages';
import { formatFileSize, formatUploadedAt, labelFor } from './format';
import { useRequest } from './useRequest';

export default function TrashPage({ session, t }) {
  const token = session?.token;
  const [working, setWorking] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const trash = useRequest(signal => token ? getTrash(token, signal) : Promise.resolve(null), [token]);
  const categories = useRequest(signal => getCategories({ signal }), []);
  const courses = useRequest(signal => getCourses({ signal }), []);

  if (!session) {
    return <section><h1>{t('trash')}</h1><p role="alert">{t('loginRequired')}</p></section>;
  }

  const categoryNames = new Map((categories.data || []).map(item => [item.category_id, item.category_name]));
  const courseNames = new Map((courses.data || []).map(item => [item.course_id, item.course_name]));

  async function run(id, action, successMsg) {
    setWorking(id); setError(''); setNotice('');
    try {
      await action();
      if (successMsg) setNotice(successMsg);
      trash.retry();
    } catch (err) {
      setError(errorKey(err));
    } finally {
      setWorking(null);
    }
  }

  function handleRestore(item) {
    run(item.material_id, () => restoreMaterial(item.material_id, token), t('trash.restored'));
  }

  function handlePermanentDelete(item) {
    if (!window.confirm(t('materials.deleteConfirm', { title: item.title }))) return;
    run(item.material_id, () => deleteMaterial(item.material_id, token), t('trash.deletedPermanent'));
  }

  function handleEmptyTrash() {
    if (!window.confirm(t('trash.emptyConfirm'))) return;
    run('empty', () => emptyTrash(token), t('trash.emptied'));
  }

  const items = trash.data?.items || [];

  return <section className="trash-page">
    <div className="page-head-row">
      <div>
        <h1>{t('trash')}</h1>
        <p className="intro">{t('trash.intro')}</p>
      </div>
      {items.length > 0 && <button className="danger-btn" disabled={working !== null} onClick={handleEmptyTrash}>
        {t('trash.emptyAction')}
      </button>}
    </div>
    {error && <p className="error-text" role="alert">{t(error)}</p>}
    {notice && <p className="success-text" role="status">{notice}</p>}
    {trash.status === 'error' ? <div role="alert"><p>{t(errorKey(trash.error))}</p><button onClick={trash.retry}>{t('retry')}</button></div>
      : trash.data === undefined ? <p>{t('loading')}</p>
        : items.length === 0 ? <p className="materials-notice">{t('trash.empty')}</p>
          : <ul className="materials-list">
            {items.map(item => <li key={item.material_id} className="materials-item" data-tone={item.category_id % 4}>
              <p className="materials-tag">{labelFor(categoryNames, item.category_id, 'materials.categoryFallback', t)}</p>
              <h2>{item.title}</h2>
              <p>{labelFor(courseNames, item.course_id, 'materials.courseFallback', t)}</p>
              <p className="materials-meta">
                {formatFileSize(item.file_size_bytes, t)} · {t('trash.deletedAt', { date: formatUploadedAt(item.deleted_at, t) })}
              </p>
              <div className="materials-item-actions row">
                <button className="primary" disabled={working !== null} onClick={() => handleRestore(item)}>
                  {t('trash.restore')}
                </button>
                <button className="danger-btn" disabled={working !== null} onClick={() => handlePermanentDelete(item)}>
                  {t('trash.deleteForever')}
                </button>
              </div>
            </li>)}
          </ul>}
  </section>;
}

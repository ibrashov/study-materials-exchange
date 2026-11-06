import React, { useEffect, useState } from 'react';
import { request, uploadMaterial } from '../../api/client';
import { errorKey } from '../../locales/messages';
export default function UploadForm({ session, t }) {
  const [choices, setChoices] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [success, setSuccess] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError('');
    Promise.all([request('/categories', { signal: controller.signal }), request('/courses', { signal: controller.signal })])
      .then(([categories, courses]) => setChoices({ categories: categories.items, courses: courses.items }))
      .catch(err => { if (!controller.signal.aborted) setError(errorKey(err)); });
    return () => controller.abort();
  }, [attempt]);
  if (!session || session.user.role !== 'student') return <p role="alert">{t(session ? 'studentRequired' : 'loginRequired')}</p>;
  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const file = data.get('file');
    setSuccess(false); setError('');
    if (!data.get('title').trim() || !data.get('category_id') || !data.get('course_id')) return setError('required');
    if (!file.size || file.size > 52428800 || !file.name.toLowerCase().endsWith('.pdf')) return setError('badFile');
    setBusy(true);
    try { await uploadMaterial(data, session.token); setSuccess(true); form.reset(); }
    catch (err) { setError(errorKey(err)); }
    finally { setBusy(false); }
  }
  return <section className="form-panel"><h1>{t('upload')}</h1><p>{t('fileHint')}</p>
    {!choices ? error ? <div role="alert">{t(error)} <button onClick={() => setAttempt(v => v + 1)}>{t('retry')}</button></div> : <p>{t('loading')}</p> :
      <form onSubmit={submit}>
        <label>{t('materialTitle')}<input name="title" required maxLength={200} disabled={busy}/></label>
        <label>{t('category')}<select aria-label={t('category')} name="category_id" required disabled={busy}><option value="">{t('choose')}</option>{choices.categories.map(c => <option key={c.category_id} value={c.category_id}>{c.category_name}</option>)}</select></label>
        <label>{t('course')}<select aria-label={t('course')} name="course_id" required disabled={busy}><option value="">{t('choose')}</option>{choices.courses.map(c => <option key={c.course_id} value={c.course_id}>{c.course_name}</option>)}</select></label>
        <label>{t('pdf')}<input name="file" type="file" accept="application/pdf,.pdf" required disabled={busy}/></label>
        {error && <p role="alert">{t(error)}</p>}{success && <p role="status">{t('uploaded')}</p>}
        <button className="primary" disabled={busy}>{t(busy ? 'saving' : 'upload')}</button>
      </form>}
  </section>;
}

import React, { useState } from 'react';
import { addCategory, addCourse } from '../../api/client';
import { errorKey } from '../../locales/messages';

function AddForm({ fields, submitLabel, send, onAdded, t }) {
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);
  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    setMessage(null);
    if (Object.values(values).some(value => !value.trim())) return setMessage({ error: 'required' });
    setBusy(true);
    try { await send(values); form.reset(); setMessage({ done: true }); onAdded(); }
    catch (err) { setMessage({ error: errorKey(err, 'taxonomy') }); }
    finally { setBusy(false); }
  }
  return <form className="admin-add-form" onSubmit={submit} noValidate>
    {fields.map(field => <label key={field.name}>{t(field.label)}<input name={field.name} maxLength={field.maxLength} disabled={busy}/></label>)}
    {message?.error && <p role="alert">{t(message.error)}</p>}{message?.done && <p role="status">{t('admin.added')}</p>}
    <button className="primary" disabled={busy}>{t(submitLabel)}</button>
  </form>;
}

export default function TaxonomyForms({ token, onAdded, t }) {
  return <section className="admin-panel" aria-labelledby="admin-taxonomy"><h2 id="admin-taxonomy">{t('admin.taxonomy')}</h2>
    <div className="admin-columns">
      <AddForm t={t} onAdded={onAdded} submitLabel="admin.addCategory" send={values => addCategory(values, token)}
        fields={[{ name: 'category_name', label: 'admin.categoryName', maxLength: 100 }]}/>
      <AddForm t={t} onAdded={onAdded} submitLabel="admin.addCourse" send={values => addCourse(values, token)}
        fields={[{ name: 'course_name', label: 'admin.courseName', maxLength: 150 }, { name: 'course_code', label: 'admin.courseCode', maxLength: 30 }]}/>
    </div></section>;
}

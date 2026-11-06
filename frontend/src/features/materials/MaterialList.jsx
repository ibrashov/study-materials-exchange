import React from 'react';
import { useLanguage } from '../../locales/LanguageContext';
import { formatFileSize, formatUploadedAt, labelFor } from './format';

export default function MaterialList({ items, categoryNames, courseNames, busy }) {
  const { t } = useLanguage();
  return <ul className="materials-list" aria-busy={busy}>
    {items.map(item => <li key={item.material_id} className="materials-item">
      <p className="materials-tag">{labelFor(categoryNames, item.category_id, 'materials.categoryFallback', t)}</p>
      <h2>{item.title}</h2>
      <p>{labelFor(courseNames, item.course_id, 'materials.courseFallback', t)}</p>
      <p className="materials-meta">{formatFileSize(item.file_size_bytes, t)} · {t('materials.uploaded', { date: formatUploadedAt(item.uploaded_at, t) })}</p>
    </li>)}
  </ul>;
}

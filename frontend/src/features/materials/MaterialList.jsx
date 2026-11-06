import React from 'react';
import { formatFileSize, formatUploadedAt, labelFor } from './format';

export default function MaterialList({ items, categoryNames, courseNames, busy }) {
  return <ul className="materials-list" aria-busy={busy}>
    {items.map(item => <li key={item.material_id} className="materials-item">
      <p className="materials-tag">{labelFor(categoryNames, item.category_id, 'Category')}</p>
      <h2>{item.title}</h2>
      <p>{labelFor(courseNames, item.course_id, 'Course')}</p>
      <p className="materials-meta">{formatFileSize(item.file_size_bytes)} · Uploaded {formatUploadedAt(item.uploaded_at)}</p>
    </li>)}
  </ul>;
}

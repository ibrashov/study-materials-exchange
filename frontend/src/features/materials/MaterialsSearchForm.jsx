import React from 'react';

const Selector = ({ id, label, allLabel, value, onChange, request, options }) => <div className="materials-field">
  <label htmlFor={id}>{label}</label>
  <select id={id} value={value} onChange={onChange} disabled={request.status !== 'success'}>
    <option value="">{allLabel}</option>
    {options}
  </select>
</div>;

export default function MaterialsSearchForm({ t, draft, onChange, onSubmit, onClear, showClear, categories, courses, filtersFailed, onRetryFilters }) {
  const update = field => event => onChange({ ...draft, [field]: event.target.value });
  return <form className="materials-search" role="search" aria-label={t('materials.searchFormLabel')}
    onSubmit={event => { event.preventDefault(); onSubmit(); }}>
    <div className="materials-field">
      <label htmlFor="materials-q">{t('materials.searchLabel')}</label>
      <input id="materials-q" type="search" placeholder={t('materials.searchPlaceholder')} value={draft.q} onChange={update('q')}/>
    </div>
    <Selector id="materials-category" label={t('category')} allLabel={t('materials.allCategories')} value={draft.categoryId}
      onChange={update('categoryId')} request={categories}
      options={categories.data?.map(item => <option key={item.category_id} value={item.category_id}>{item.category_name}</option>)}/>
    <Selector id="materials-course" label={t('course')} allLabel={t('materials.allCourses')} value={draft.courseId}
      onChange={update('courseId')} request={courses}
      options={courses.data?.map(item => <option key={item.course_id} value={item.course_id}>{item.course_name} ({item.course_code})</option>)}/>
    <div className="materials-actions">
      <button type="submit" className="materials-submit">{t('search')}</button>
      {showClear && <button type="button" onClick={onClear}>{t('materials.clear')}</button>}
      {filtersFailed && <>
        <span className="materials-hint">{t('materials.filtersFailed')}</span>
        <button type="button" onClick={onRetryFilters}>{t('materials.retryFilters')}</button>
      </>}
    </div>
  </form>;
}

import React from 'react';

const Selector = ({ id, label, allLabel, value, onChange, request, options }) => <div className="materials-field">
  <label htmlFor={id}>{label}</label>
  <select id={id} value={value} onChange={onChange} disabled={request.status !== 'success'}>
    <option value="">{allLabel}</option>
    {options}
  </select>
</div>;

export default function MaterialsSearchForm({ draft, onChange, onSubmit, onClear, showClear, categories, courses, filtersFailed, onRetryFilters }) {
  const update = field => event => onChange({ ...draft, [field]: event.target.value });
  return <form className="materials-search" role="search" aria-label="Search study materials"
    onSubmit={event => { event.preventDefault(); onSubmit(); }}>
    <div className="materials-field">
      <label htmlFor="materials-q">Search</label>
      <input id="materials-q" type="search" placeholder="Title or course name" value={draft.q} onChange={update('q')}/>
    </div>
    <Selector id="materials-category" label="Category" allLabel="All categories" value={draft.categoryId}
      onChange={update('categoryId')} request={categories}
      options={categories.data?.map(item => <option key={item.category_id} value={item.category_id}>{item.category_name}</option>)}/>
    <Selector id="materials-course" label="Course" allLabel="All courses" value={draft.courseId}
      onChange={update('courseId')} request={courses}
      options={courses.data?.map(item => <option key={item.course_id} value={item.course_id}>{item.course_name} ({item.course_code})</option>)}/>
    <div className="materials-actions">
      <button type="submit" className="materials-submit">Search</button>
      {showClear && <button type="button" onClick={onClear}>Clear search</button>}
      {filtersFailed && <>
        <span className="materials-hint">Category and course filters are unavailable right now.</span>
        <button type="button" onClick={onRetryFilters}>Retry filters</button>
      </>}
    </div>
  </form>;
}

import React, { useMemo, useState } from 'react';
import { getCategories, getCourses, getMaterials } from '../../api/client';
import MaterialList from './MaterialList';
import MaterialsSearchForm from './MaterialsSearchForm';
import { describeLoadError, resultsSummary } from './format';
import { useRequest } from './useRequest';
import './materials.css';

const PAGE_SIZE = 20;
const NO_FILTERS = { q: '', categoryId: '', courseId: '' };
const isFiltered = filters => Boolean(filters.q.trim() || filters.categoryId || filters.courseId);

export default function MaterialsPage({ session, t = key => key }) {
  const [draft, setDraft] = useState(NO_FILTERS);
  const [search, setSearch] = useState({ filters: NO_FILTERS, offset: 0 });
  const categories = useRequest(signal => getCategories({ signal }), []);
  const courses = useRequest(signal => getCourses({ signal }), []);
  const materials = useRequest(
    signal => getMaterials({ ...search.filters, limit: PAGE_SIZE, offset: search.offset, signal }),
    [search],
  );
  const categoryNames = useMemo(
    () => new Map(categories.data?.map(item => [item.category_id, item.category_name])),
    [categories.data],
  );
  const courseNames = useMemo(
    () => new Map(courses.data?.map(item => [item.course_id, `${item.course_name} (${item.course_code})`])),
    [courses.data],
  );

  const retryFilters = () => {
    if (categories.status === 'error') categories.retry();
    if (courses.status === 'error') courses.retry();
  };
  const retryAll = () => { materials.retry(); retryFilters(); };
  const clearSearch = () => { setDraft(NO_FILTERS); setSearch({ filters: NO_FILTERS, offset: 0 }); };
  const goToOffset = offset => setSearch(current => ({ ...current, offset }));

  const filtersSettled = categories.status !== 'loading' && courses.status !== 'loading';
  const busy = materials.status === 'loading';
  const failure = materials.status === 'error' ? describeLoadError(materials.error) : null;
  const loading = !failure && (busy || !filtersSettled);
  const results = filtersSettled ? materials.data : undefined;

  return <section aria-labelledby="materials-title">
    <p className="eyebrow">STUDY MATERIALS</p>
    <h1 id="materials-title">Find study materials</h1>
    <p className="intro">Browse and search notes, presentations and course resources shared by students.</p>
    <MaterialsSearchForm draft={draft} onChange={setDraft} categories={categories} courses={courses}
      onSubmit={() => setSearch({ filters: draft, offset: 0 })} onClear={clearSearch}
      showClear={isFiltered(draft) || isFiltered(search.filters)}
      filtersFailed={!failure && (categories.status === 'error' || courses.status === 'error')} onRetryFilters={retryFilters}/>
    <div className={failure ? `materials-notice materials-notice-${failure.kind}` : 'materials-summary'}>
      <div role="status" aria-live="polite">
        {loading && <p>Loading materials…</p>}
        {failure && <><h2>{failure.title}</h2><p>{failure.message}</p></>}
        {!loading && !failure && <p>{resultsSummary({
          total: results.total, offset: results.offset, count: results.items.length, filtered: isFiltered(search.filters),
        })}</p>}
      </div>
      {failure && <button onClick={retryAll}>Try again</button>}
    </div>
    {results?.items.length > 0 && <MaterialList items={results.items} categoryNames={categoryNames} courseNames={courseNames} busy={busy} session={session} t={t}/>}
    {results && (results.offset > 0 || results.total > results.items.length) && <nav className="materials-pager" aria-label="Materials pages">
      <button onClick={() => goToOffset(Math.max(0, results.offset - results.limit))} disabled={busy || results.offset === 0}>Previous</button>
      <button onClick={() => goToOffset(results.offset + results.limit)}
        disabled={busy || results.items.length === 0 || results.offset + results.items.length >= results.total}>Next</button>
    </nav>}
  </section>;
}

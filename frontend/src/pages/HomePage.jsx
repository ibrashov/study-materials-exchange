import React, { useState } from 'react';
import BackendStatus from '../components/BackendStatus';
import { getCategories } from '../api/client';
import { useRequest } from '../features/materials/useRequest';
export default function HomePage({ t, session, onSearch, onNavigate }) {
  const [q, setQ] = useState('');
  const categories = useRequest(signal => getCategories({ signal }), []);
  return <><section className="hero" aria-labelledby="home-title">
    <h1 id="home-title">{t('home.title')}</h1><p className="intro">{t('home.intro')}</p>
    <form className="hero-search" role="search" onSubmit={e => { e.preventDefault(); onSearch({ q }); }}>
      <label htmlFor="home-q" className="visually-hidden">{t('searchLabel')}</label>
      <input id="home-q" type="search" value={q} onChange={e => setQ(e.target.value)} placeholder={t('home.placeholder')} maxLength={200}/>
      <button className="primary" type="submit">{t('search')}</button>
    </form>
    {categories.status === 'success' && categories.data.length > 0 && <div className="chips" role="group" aria-label={t('home.browse')}>
      <span className="chips-label">{t('home.browse')}</span>
      {categories.data.map(c => <button key={c.category_id} className="chip" data-tone={c.category_id % 4} onClick={() => onSearch({ categoryId: String(c.category_id) })}>{c.category_name}</button>)}
    </div>}
    <p className="share"><button className="link" onClick={() => onNavigate(session ? 'upload' : 'registration')}>{t('home.share')}</button></p>
  </section><BackendStatus t={t}/></>;
}

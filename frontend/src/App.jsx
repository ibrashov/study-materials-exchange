import React from 'react';
import { useState } from 'react';
import HomePage from './pages/HomePage';
import MaterialsPage from './features/materials/MaterialsPage';
const modules = {Login: 'Alibek: login UI; Talgat: authentication', Registration: 'Alibek: registration UI; Talgat: account creation', Materials: 'Alibek: materials UI; Daryn: search; Talgat: data operations', Upload: 'Alibek: upload UI; Daryn: file handling', Admin: 'Arnur: admin functionality and role tests'};
export default function App() {
  const [page, setPage] = useState('Home');
  return <div className="shell"><header><a href="#home" onClick={() => setPage('Home')} className="brand">SME / Study together</a><span>Integration preview</span></header>
    <nav aria-label="Main navigation">{['Home', ...Object.keys(modules)].map(name => <button key={name} aria-current={page === name ? 'page' : undefined} onClick={() => setPage(name)}>{name}</button>)}</nav>
    <main>{page === 'Home' ? <HomePage/> : page === 'Materials' ? <MaterialsPage/> : <section><p className="eyebrow">PLANNED MODULE</p><h1>{page}</h1><p>This feature is not implemented yet.</p><p>{modules[page]}</p><button onClick={() => setPage('Home')}>Back to overview</button></section>}</main>
    <footer>React + Vite ? FastAPI ? PostgreSQL integration planned</footer></div>;
}

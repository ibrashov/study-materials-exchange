import React from 'react';
import { useState } from 'react';
import HomePage from './pages/HomePage';
import MaterialsPage from './features/materials/MaterialsPage';
import LanguageSwitcher from './locales/LanguageSwitcher';
import { useLanguage } from './locales/LanguageContext';

const pages = ['Home', 'Login', 'Registration', 'Materials', 'Upload', 'Admin'];

export default function App() {
  const { t } = useLanguage();
  const [page, setPage] = useState('Home');
  return <div className="shell"><header><a href="#home" onClick={() => setPage('Home')} className="brand">{t('brand')}</a><div className="header-tools"><span>{t('header.preview')}</span><LanguageSwitcher/></div></header>
    <nav aria-label={t('nav.label')}>{pages.map(name => <button key={name} aria-current={page === name ? 'page' : undefined} onClick={() => setPage(name)}>{t(`nav.${name}`)}</button>)}</nav>
    <main>{page === 'Home' ? <HomePage/> : page === 'Materials' ? <MaterialsPage/> : <section><p className="eyebrow">{t('planned.eyebrow')}</p><h1>{t(`nav.${page}`)}</h1><p>{t('planned.body')}</p><p>{t(`planned.${page}`)}</p><button onClick={() => setPage('Home')}>{t('planned.back')}</button></section>}</main>
    <footer>{t('footer')}</footer></div>;
}

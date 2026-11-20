import React, { useEffect, useMemo, useRef, useState } from 'react';
import HomePage from './pages/HomePage';
import AuthForm from './features/auth/AuthForm';
import SecurityPage from './features/auth/SecurityPage';
import Materials from './features/materials/MaterialsPage';
import TrashPage from './features/materials/TrashPage';
import UploadForm from './features/materials/UploadForm';
import GamificationPage from './features/gamification/GamificationPage';
import ProfilePage from './features/gamification/ProfilePage';
import AdminPage from './features/admin/AdminPage';
import ChatWidget from './features/chat/ChatWidget';
import { createTranslator, pickLanguage } from './locales/messages';
const pages = ['home', 'materials', 'leaderboard', 'registration', 'login', 'upload', 'trash', 'security', 'admin'];
const languages = [['en', 'EN'], ['ru', 'RU'], ['kk', 'ҚАЗ']];
// "#materials" opens a page; "#profile/7" opens the public profile of student 7.
const currentRoute = () => {
  const [name, id] = location.hash.slice(1).split('/');
  if (name === 'profile' && /^[1-9]\d{0,9}$/.test(id ?? '')) return { page: 'profile', profileId: Number(id) };
  return { page: pages.includes(name) ? name : 'home', profileId: null };
};
const LANGUAGE_KEY = 'sme-language';
function savedLanguage() {
  try { return pickLanguage(localStorage.getItem(LANGUAGE_KEY)); } catch { return pickLanguage(); }
}
export default function App() {
  const [route, setRoute] = useState(currentRoute);
  const { page, profileId } = route;
  const [language, setLanguage] = useState(savedLanguage);
  const [session, setSession] = useState(null);
  const [preset, setPreset] = useState({ q: '', categoryId: '', courseId: '' });
  const t = useMemo(() => createTranslator(language), [language]);
  const mainRef = useRef(null);
  const shownPage = useRef(page);
  useEffect(() => { const change = () => setRoute(currentRoute()); window.addEventListener('hashchange', change); return () => window.removeEventListener('hashchange', change); }, []);
  useEffect(() => {
    document.documentElement.lang = language;
    try { localStorage.setItem(LANGUAGE_KEY, language); } catch { /* Blocked storage only loses the saved choice. */ }
  }, [language]);
  useEffect(() => {
    if (shownPage.current === page) return;
    shownPage.current = page;
    mainRef.current?.focus();
  }, [page]);
  const navigate = name => { location.hash = name; setRoute({ page: name, profileId: null }); };
  const search = filters => { setPreset({ q: '', categoryId: '', courseId: '', ...filters }); navigate('materials'); };
  const visiblePages = pages.filter(name => {
    if (name === 'admin') return session?.user.role === 'admin';
    if (name === 'security' || name === 'trash') return Boolean(session);
    if (['login', 'registration'].includes(name)) return !session;
    return true;
  });
  return <div className="shell"><a className="skip-link" href="#main" onClick={event => { event.preventDefault(); mainRef.current?.focus(); }}>{t('skip')}</a><header><a href="#home" className="brand"><span className="brand-mark" aria-hidden="true">SM</span>Study Materials Exchange</a>
    <div className="account"><span className="who">{session?.user.role === 'student'
      ? <a href={`#profile/${session.user.user_id}`}>{session.user.full_name}</a> : session?.user.full_name}</span><label className="language">{t('language')}<select value={language} onChange={e => setLanguage(e.target.value)}>{languages.map(([code, label]) => <option key={code} value={code}>{label}</option>)}</select></label></div></header>
    <nav aria-label="Main navigation">{visiblePages.map(name =>
      <button key={name} aria-current={page === name ? 'page' : undefined} onClick={() => navigate(name)}>{t(name)}</button>)}
      {session && <button className="quiet" onClick={() => { setSession(null); navigate('home'); }}>{t('logout')}</button>}
    </nav><main ref={mainRef} tabIndex={-1}>
      {page === 'home' && <HomePage t={t} session={session} onSearch={search} onNavigate={navigate}/>}
      {page === 'materials' && <Materials key={JSON.stringify(preset)} preset={preset} t={t} session={session}/>}
      {page === 'leaderboard' && <GamificationPage t={t} session={session}/>}
      {page === 'profile' && <ProfilePage key={profileId} userId={profileId} t={t} session={session} onSearch={search}/>}
      {['login', 'registration'].includes(page) && <AuthForm key={page} mode={page} t={t} onLogin={value => { setSession(value); navigate('home'); }}/>}
      {page === 'upload' && <UploadForm t={t} session={session}/>}
      {page === 'trash' && <TrashPage t={t} session={session}/>}
      {page === 'security' && <SecurityPage t={t} session={session} onChange={user => setSession(current => ({ ...current, user }))}/>}
      {page === 'admin' && <AdminPage t={t} session={session}/>}
    </main><ChatWidget t={t} session={session}/><footer>{t('footer')}</footer></div>;
}

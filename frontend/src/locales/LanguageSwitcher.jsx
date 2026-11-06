import React from 'react';
import { useLanguage } from './LanguageContext';
import { LANGUAGES } from './translate';
import './language.css';

export default function LanguageSwitcher() {
  const { language, setLanguage, t } = useLanguage();
  return <div className="language-switcher" role="group" aria-label={t('language.label')}>
    {LANGUAGES.map(({ code, label, name }) => <button key={code} lang={code} aria-label={name}
      aria-pressed={language === code} onClick={() => setLanguage(code)}>{label}</button>)}
  </div>;
}

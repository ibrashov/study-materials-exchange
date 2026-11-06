import React from 'react';
import BackendStatus from '../components/BackendStatus';
import { useLanguage } from '../locales/LanguageContext';
export default function HomePage() {
  const { t } = useLanguage();
  return <><p className="eyebrow">{t('home.eyebrow')}</p><h1>{t('home.title')}</h1>
    <p className="intro">{t('home.intro')}</p>
    <BackendStatus/><section><h2>{t('home.sectionTitle')}</h2><p>{t('home.sectionBody')}</p></section></>;
}

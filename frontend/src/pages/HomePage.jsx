import React from 'react';
import BackendStatus from '../components/BackendStatus';
export default function HomePage({ t, session }) {
  return <><h1>{t('title')}</h1><p className="intro">{t('intro')}</p>
    <a href="#materials">{t('materials')}</a><BackendStatus t={t}/></>;
}

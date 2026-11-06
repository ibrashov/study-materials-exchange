import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { createTranslator, pickLanguage } from './translate';

const STORAGE_KEY = 'sme-language';
const LanguageContext = createContext(null);

function readSavedLanguage() {
  try {
    return pickLanguage(localStorage.getItem(STORAGE_KEY));
  } catch {
    return pickLanguage();
  }
}

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(readSavedLanguage);
  useEffect(() => {
    document.documentElement.lang = language;
    try {
      localStorage.setItem(STORAGE_KEY, language);
    } catch {
      // Storage can be blocked; the choice then lasts until the page closes.
    }
  }, [language]);
  const value = useMemo(() => ({ language, setLanguage, t: createTranslator(language) }), [language]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export const useLanguage = () => useContext(LanguageContext);

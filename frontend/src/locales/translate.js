import en from './en.js';
import ru from './ru.js';

const dictionaries = { en, ru };
const DEFAULT_LANGUAGE = 'en';

export const LANGUAGES = [
  { code: 'en', label: 'EN', name: 'English' },
  { code: 'ru', label: 'RU', name: 'Русский' },
];

export const pickLanguage = language => (Object.hasOwn(dictionaries, language ?? '') ? language : DEFAULT_LANGUAGE);

export function createTranslator(language) {
  const dictionary = dictionaries[pickLanguage(language)];
  return (key, values) => {
    const text = dictionary[key];
    if (text === undefined) return key;
    return typeof text === 'function' ? text(values) : text;
  };
}

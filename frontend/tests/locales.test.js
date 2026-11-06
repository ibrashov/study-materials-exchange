import { test } from 'node:test';
import assert from 'node:assert/strict';
import en from '../src/locales/en.js';
import ru from '../src/locales/ru.js';
import { createTranslator, pickLanguage } from '../src/locales/translate.js';

test('English and Russian define the same keys', () => {
  assert.deepEqual(Object.keys(ru).sort(), Object.keys(en).sort());
});

test('dynamic text stays dynamic in both languages', () => {
  const mismatched = Object.keys(en).filter(key => typeof en[key] !== typeof ru[key]);
  assert.deepEqual(mismatched, []);
});

test('Russian text is really translated', () => {
  const values = { from: 1, to: 2, total: 3, id: 4, date: 'x', service: 'x', status: 'x', details: 'x' };
  const untranslated = Object.keys(ru)
    .filter(key => key !== 'locale')
    .filter(key => !/[А-Яа-я]/.test(typeof ru[key] === 'function' ? ru[key](values) : ru[key]));
  assert.deepEqual(untranslated, []);
});

test('a translator returns text in the chosen language', () => {
  assert.equal(createTranslator('en')('nav.Materials'), 'Materials');
  assert.equal(createTranslator('ru')('nav.Materials'), 'Материалы');
});

test('a translator fills values into dynamic text', () => {
  assert.equal(createTranslator('ru')('materials.summary', { from: 21, to: 40, total: 45 }), 'Показано 21–40 из 45');
});

test('English counts agree with their noun', () => {
  const t = createTranslator('en');
  assert.equal(t('materials.summary', { from: 1, to: 1, total: 1 }), 'Showing 1–1 of 1 material');
  assert.equal(t('materials.summary', { from: 1, to: 2, total: 2 }), 'Showing 1–2 of 2 materials');
});

test('an unsupported language falls back to English', () => {
  assert.equal(createTranslator('de')('nav.Home'), 'Home');
});

test('an unknown key is shown as the key', () => {
  assert.equal(createTranslator('en')('missing.key'), 'missing.key');
});

test('pickLanguage accepts only supported languages', () => {
  assert.equal(pickLanguage('ru'), 'ru');
  assert.equal(pickLanguage('en'), 'en');
  assert.equal(pickLanguage('de'), 'en');
  assert.equal(pickLanguage(null), 'en');
  assert.equal(pickLanguage('__proto__'), 'en');
});

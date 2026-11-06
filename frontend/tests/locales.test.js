import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createTranslator, errorKey, messages, pickLanguage } from '../src/locales/messages.js';

const { en, ru } = messages;
const sample = { from: 1, to: 2, total: 3, id: 4, date: 'x', service: 'x', status: 'x', details: 'x', title: 'x', count: 1 };

test('English and Russian define the same keys', () => {
  assert.deepEqual(Object.keys(ru).sort(), Object.keys(en).sort());
});

test('dynamic text stays dynamic in both languages', () => {
  assert.deepEqual(Object.keys(en).filter(key => typeof en[key] !== typeof ru[key]), []);
});

test('Russian text is really translated', () => {
  const untranslated = Object.keys(ru).filter(key => key !== 'locale')
    .filter(key => !/[А-Яа-я]/.test(typeof ru[key] === 'function' ? ru[key](sample) : ru[key]));
  assert.deepEqual(untranslated, []);
});

test('a translator fills values into dynamic text', () => {
  assert.equal(createTranslator('ru')('materials.summary', { from: 21, to: 40, total: 45 }), 'Показано 21–40 из 45');
  assert.equal(createTranslator('en')('materials.summary', { from: 1, to: 1, total: 1 }), 'Showing 1–1 of 1 material');
});

test('an unsupported language falls back to English and an unknown key shows itself', () => {
  assert.equal(createTranslator('de')('home'), 'Home');
  assert.equal(createTranslator('en')('missing.key'), 'missing.key');
});

test('pickLanguage accepts only supported languages', () => {
  assert.equal(pickLanguage('ru'), 'ru');
  assert.equal(pickLanguage(null), 'en');
  assert.equal(pickLanguage('__proto__'), 'en');
});

test('errorKey separates a blocked account from a wrong password', () => {
  assert.equal(errorKey({ status: 403 }, 'login'), 'accountDisabled');
  assert.equal(errorKey({ status: 401 }, 'login'), 'invalidLogin');
  assert.equal(errorKey({ status: 403 }), 'denied');
});

test('errorKey explains conflicts by context', () => {
  assert.equal(errorKey({ status: 409 }), 'duplicate');
  assert.equal(errorKey({ status: 409 }, 'taxonomy'), 'duplicateItem');
  assert.equal(errorKey({ status: 409 }, 'user'), 'selfChange');
});

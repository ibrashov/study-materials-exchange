import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createTranslator } from '../src/locales/messages.js';
import { activityWeeks, eventText, formatDay, formatPoints, heatLevel } from '../src/features/gamification/format.js';

const en = createTranslator('en');
const ru = createTranslator('ru');

test('material events are translated around the title', () => {
  const event = { action: 'upload_material', material_title: 'Graphs', description: 'Uploaded "Graphs"' };
  assert.equal(eventText(event, en), 'Uploaded “Graphs”');
  assert.equal(eventText(event, ru), 'Загружен материал «Graphs»');
});

test('a deleted material keeps its title from the stored description', () => {
  const event = { action: 'upload_revoked', material_title: null, description: 'Removed "Old draft"' };
  assert.equal(eventText(event, en), 'Removed “Old draft”, upload XP returned');
});

test('a private download never shows what was studied', () => {
  const event = { action: 'download_material', material_title: null, description: 'Studied a material' };
  assert.equal(eventText(event, ru), 'Изучен учебный материал');
});

test('other events are translated and unknown ones fall back to the description', () => {
  assert.equal(eventText({ action: 'enable_2fa', description: 'x' }, ru), 'Включена двухфакторная аутентификация');
  assert.equal(eventText({ action: 'future_action', description: 'Did something' }, en), 'Did something');
});

test('points show their sign', () => {
  assert.equal(formatPoints(50), '+50');
  assert.equal(formatPoints(-50), '−50');
});

test('the heatmap covers whole weeks ending today', () => {
  const weeks = activityWeeks([{ date: '2026-11-20', xp: 55 }], '2026-11-20', 84);
  assert.equal(weeks[0][0].date, '2026-08-24'); // a Monday
  assert.ok(weeks.slice(0, -1).every(week => week.length === 7));
  const last = weeks.at(-1);
  assert.deepEqual(last.at(-1), { date: '2026-11-20', xp: 55 });
  assert.equal(last.length, 5); // Monday 16 Nov to Friday 20 Nov
  assert.deepEqual([0, 5, 20, 45, 90].map(heatLevel), [0, 1, 2, 3, 4]);
});

test('a study day is printed as the same calendar date in every language', () => {
  assert.equal(formatDay('2026-11-20', en), '20 Nov 2026');
  assert.match(formatDay('2026-11-20', ru), /^20 нояб/);
});

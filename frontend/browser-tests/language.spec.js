import { test, expect } from '@playwright/test';

const headers = { 'access-control-allow-origin': '*', 'content-type': 'application/json' };
const fulfillJson = (route, body) => route.fulfill({ status: 200, headers, body: JSON.stringify(body) });

async function mockLibrary(page) {
  const queries = [];
  await page.route('**/api/categories', route => fulfillJson(route, {
    items: [{ category_id: 1, category_name: 'Notes', description: null, created_at: '2026-11-05T08:00:00Z' }],
  }));
  await page.route('**/api/courses', route => fulfillJson(route, {
    items: [{ course_id: 1, course_name: 'Database Systems', course_code: 'DB101', description: null }],
  }));
  await page.route('**/api/materials?*', route => {
    queries.push(new URL(route.request().url()).searchParams);
    return fulfillJson(route, {
      items: [{ material_id: 1, uploader_id: 1, category_id: 1, course_id: 1, title: 'Example notes', file_size_bytes: 1536, uploaded_at: '2026-11-05T12:00:00Z' }],
      total: 1, limit: 20, offset: 0,
    });
  });
  return queries;
}

const chooseRussian = page => page.getByRole('button', { name: 'Русский' }).click();

test('starts in English and switches to Russian and back', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Materials', exact: true })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');

  await chooseRussian(page);
  await expect(page.getByRole('button', { name: 'Материалы', exact: true })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
  await expect(page.getByRole('button', { name: 'Русский' })).toHaveAttribute('aria-pressed', 'true');

  await page.getByRole('button', { name: 'English' }).click();
  await expect(page.getByRole('button', { name: 'Materials', exact: true })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
});

test('the backend status panel is translated', async ({ page }) => {
  await page.route('**/api/health', route => route.abort());
  await page.goto('/');
  await chooseRussian(page);
  await expect(page.getByRole('status')).toContainText('Не удалось подключиться к серверу');
  await expect(page.getByRole('button', { name: 'Проверить подключение' })).toBeVisible();
});

test('remembers the chosen language after a reload', async ({ page }) => {
  await page.goto('/');
  await chooseRussian(page);
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
  await page.reload();
  await expect(page.getByRole('button', { name: 'Материалы', exact: true })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
});

test('planned modules are translated', async ({ page }) => {
  await page.goto('/');
  await chooseRussian(page);
  await page.getByRole('button', { name: 'Вход', exact: true }).click();
  await expect(page.getByText('Эта функция пока не реализована.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Вернуться к обзору' })).toBeVisible();
});

test('the materials page and its results are translated', async ({ page }) => {
  await mockLibrary(page);
  await page.goto('/');
  await chooseRussian(page);
  await page.getByRole('button', { name: 'Материалы', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Показано 1–1 из 1');
  await expect(page.getByLabel('Поиск', { exact: true })).toBeVisible();
  await expect(page.getByLabel('Категория')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Найти', exact: true })).toBeVisible();
  const item = page.getByRole('listitem');
  await expect(item).toContainText('1,5 КБ');
  await expect(item).toContainText('5 нояб');
  await expect(item).toContainText('Example notes');
});

test('the not available message is translated', async ({ page }) => {
  const notFound = { status: 404, headers, body: JSON.stringify({ error: { code: 'http_404', message: 'Not Found' } }) };
  await page.route('**/api/categories', route => route.fulfill(notFound));
  await page.route('**/api/courses', route => route.fulfill(notFound));
  await page.route('**/api/materials?*', route => route.fulfill(notFound));
  await page.goto('/');
  await chooseRussian(page);
  await page.getByRole('button', { name: 'Материалы', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Материалы пока недоступны');
  await expect(page.getByRole('button', { name: 'Повторить' })).toBeVisible();
});

test('changing language keeps the open page and the current search', async ({ page }) => {
  const queries = await mockLibrary(page);
  await page.goto('/');
  await page.getByRole('button', { name: 'Materials', exact: true }).click();
  await page.getByLabel('Search', { exact: true }).fill('notes');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect.poll(() => queries.at(-1)?.get('q')).toBe('notes');
  const requestsBefore = queries.length;

  await chooseRussian(page);
  await expect(page.getByRole('status')).toContainText('Показано 1–1 из 1');
  await expect(page.getByLabel('Поиск', { exact: true })).toHaveValue('notes');
  expect(queries.length).toBe(requestsBefore);
});

test('still switches language when the browser blocks storage', async ({ page }) => {
  await page.addInitScript(() => {
    Storage.prototype.getItem = () => { throw new Error('blocked'); };
    Storage.prototype.setItem = () => { throw new Error('blocked'); };
  });
  await page.goto('/');
  await chooseRussian(page);
  await expect(page.getByRole('button', { name: 'Материалы', exact: true })).toBeVisible();
});

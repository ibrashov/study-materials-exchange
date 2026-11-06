import { test, expect } from '@playwright/test';

// Isolate search UI states with contract-shaped API responses.
// week10.spec.js separately exercises the real PostgreSQL/upload/download workflow.
const headers = { 'access-control-allow-origin': '*', 'content-type': 'application/json' };
const categories = [
  { category_id: 1, category_name: 'Notes', description: null, created_at: '2026-11-05T08:00:00Z' },
  { category_id: 2, category_name: 'Presentations', description: null, created_at: '2026-11-05T08:00:00Z' },
];
const courses = [
  { course_id: 1, course_name: 'Introduction to Programming', course_code: 'PROG101', description: null },
  { course_id: 2, course_name: 'Database Systems', course_code: 'DB101', description: null },
];
const material = (id, overrides = {}) => ({
  material_id: id, uploader_id: 1, category_id: 1, course_id: 1,
  title: `Material ${id}`, file_size_bytes: 1024, uploaded_at: '2026-11-05T12:00:00Z', ...overrides,
});
const notFound = { status: 404, headers, body: JSON.stringify({ error: { code: 'http_404', message: 'Not Found' } }) };
const fulfillJson = (route, body) => route.fulfill({ status: 200, headers, body: JSON.stringify(body) });

async function mockFilters(page) {
  await page.route('**/api/categories', route => fulfillJson(route, { items: categories }));
  await page.route('**/api/courses', route => fulfillJson(route, { items: courses }));
}

// Serves a library of `total` materials and records every query the page sends.
async function mockMaterials(page, total, match = () => true) {
  const queries = [];
  await page.route('**/api/materials?*', route => {
    const query = new URL(route.request().url()).searchParams;
    queries.push(query);
    const limit = Number(query.get('limit'));
    const offset = Number(query.get('offset'));
    const matched = Array.from({ length: total }, (_, index) => material(index + 1)).filter(() => match(query));
    return fulfillJson(route, { items: matched.slice(offset, offset + limit), total: matched.length, limit, offset });
  });
  return queries;
}

async function openMaterials(page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'Materials', exact: true }).click();
}

test('lists a material with its category, course, size and date', async ({ page }) => {
  await mockFilters(page);
  await page.route('**/api/materials?*', route => fulfillJson(route, {
    items: [material(1, { title: 'Example programming notes' })], total: 1, limit: 20, offset: 0,
  }));
  await openMaterials(page);
  await expect(page.getByRole('status')).toContainText('Showing 1–1 of 1 material');
  const item = page.getByRole('listitem').filter({ hasText: 'Example programming notes' });
  await expect(item).toContainText('Notes');
  await expect(item).toContainText('Introduction to Programming (PROG101)');
  await expect(item).toContainText('1.0 KB');
  await expect(item).toContainText('5 Nov 2026');
});

test('shows a loading state until the materials arrive', async ({ page }) => {
  await mockFilters(page);
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  await page.route('**/api/materials?*', async route => {
    await gate;
    await fulfillJson(route, { items: [material(1)], total: 1, limit: 20, offset: 0 });
  });
  await openMaterials(page);
  await expect(page.getByRole('status')).toContainText('Loading materials');
  release();
  await expect(page.getByRole('status')).toContainText('Showing 1–1 of 1 material');
});

test('search sends the text and filters and returns to the first page', async ({ page }) => {
  await mockFilters(page);
  const queries = await mockMaterials(page, 45);
  await openMaterials(page);
  await expect(page.getByRole('status')).toContainText('Showing 1–20 of 45');
  await page.getByRole('button', { name: 'Next' }).click();
  await expect(page.getByRole('status')).toContainText('Showing 21–40 of 45');

  await page.getByLabel('Search', { exact: true }).fill('  programming ');
  await page.getByLabel('Category').selectOption({ label: 'Presentations' });
  await page.getByLabel('Course').selectOption({ label: 'Database Systems (DB101)' });
  await page.getByRole('button', { name: 'Search', exact: true }).click();

  await expect.poll(() => queries.at(-1)?.toString())
    .toBe('q=programming&category_id=2&course_id=2&limit=20&offset=0');
});

test('pressing Enter in the search box runs the search', async ({ page }) => {
  await mockFilters(page);
  const queries = await mockMaterials(page, 1);
  await openMaterials(page);
  await page.getByLabel('Search', { exact: true }).fill('notes');
  await page.getByLabel('Search', { exact: true }).press('Enter');
  await expect.poll(() => queries.at(-1)?.get('q')).toBe('notes');
});

test('an empty search can be cleared to see every material again', async ({ page }) => {
  await mockFilters(page);
  const queries = await mockMaterials(page, 2, query => !query.has('q'));
  await openMaterials(page);
  await page.getByLabel('Search', { exact: true }).fill('no such thing');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('No materials match your search.');
  await expect(page.getByRole('listitem')).toHaveCount(0);

  await page.getByRole('button', { name: 'Clear search' }).click();
  await expect(page.getByRole('status')).toContainText('Showing 1–2 of 2 materials');
  await expect(page.getByLabel('Search', { exact: true })).toHaveValue('');
  expect(queries.at(-1).has('q')).toBe(false);
});

test('an empty library is not described as a failed search', async ({ page }) => {
  await mockFilters(page);
  await mockMaterials(page, 0);
  await openMaterials(page);
  await expect(page.getByRole('status')).toContainText('No materials have been uploaded yet.');
  await expect(page.getByRole('button', { name: 'Clear search' })).toHaveCount(0);
});

test('Next and Previous move through the pages and stop at the ends', async ({ page }) => {
  await mockFilters(page);
  await mockMaterials(page, 25);
  await openMaterials(page);
  await expect(page.getByRole('status')).toContainText('Showing 1–20 of 25');
  await expect(page.getByRole('button', { name: 'Previous' })).toBeDisabled();

  await page.getByRole('button', { name: 'Next' }).click();
  await expect(page.getByRole('status')).toContainText('Showing 21–25 of 25');
  await expect(page.getByRole('button', { name: 'Next' })).toBeDisabled();

  await page.getByRole('button', { name: 'Previous' }).click();
  await expect(page.getByRole('status')).toContainText('Showing 1–20 of 25');
});

test('says the service is not available yet when the endpoints are not mounted', async ({ page }) => {
  await page.route('**/api/categories', route => route.fulfill(notFound));
  await page.route('**/api/courses', route => route.fulfill(notFound));
  await page.route('**/api/materials?*', route => route.fulfill(notFound));
  await openMaterials(page);
  await expect(page.getByRole('status')).toContainText('Materials aren’t available yet');
  await expect(page.getByRole('listitem')).toHaveCount(0);
  await expect(page.getByLabel('Category')).toBeDisabled();
  await expect(page.getByLabel('Course')).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Retry filters' })).toHaveCount(0);
});

test('recovers from a network failure with Try again', async ({ page }) => {
  await mockFilters(page);
  await page.route('**/api/materials?*', route => route.abort());
  await openMaterials(page);
  await expect(page.getByRole('status')).toContainText('Cannot connect to the backend');

  await page.unroute('**/api/materials?*');
  await mockMaterials(page, 3);
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect(page.getByRole('status')).toContainText('Showing 1–3 of 3 materials');
});

test('still lists materials when the filters cannot be loaded', async ({ page }) => {
  await page.route('**/api/categories', route => route.fulfill(notFound));
  await page.route('**/api/courses', route => route.fulfill(notFound));
  await mockMaterials(page, 1);
  await openMaterials(page);
  await expect(page.getByRole('listitem')).toContainText('Category #1');
  await expect(page.getByRole('listitem')).toContainText('Course #1');
  await expect(page.getByText('filters are unavailable')).toBeVisible();

  await page.unroute('**/api/categories');
  await page.unroute('**/api/courses');
  await mockFilters(page);
  await page.getByRole('button', { name: 'Retry filters' }).click();
  await expect(page.getByLabel('Category')).toBeEnabled();
  await expect(page.getByRole('listitem')).toContainText('Introduction to Programming (PROG101)');
});

test('a slow earlier search cannot replace newer results', async ({ page }) => {
  await mockFilters(page);
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  let slowFinished;
  const slowDone = new Promise(resolve => { slowFinished = resolve; });
  await page.route('**/api/materials?*', async route => {
    const slow = new URL(route.request().url()).searchParams.get('q') === 'slow';
    if (slow) await gate;
    const title = slow ? 'Slow result' : 'Newest result';
    await fulfillJson(route, { items: [material(1, { title })], total: 1, limit: 20, offset: 0 }).catch(() => {});
    if (slow) slowFinished();
  });
  await openMaterials(page);
  await page.getByLabel('Search', { exact: true }).fill('slow');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await page.getByLabel('Search', { exact: true }).fill('newest');
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(page.getByRole('listitem')).toContainText('Newest result');

  release();
  await slowDone;
  await page.waitForTimeout(300); // Gives a wrongly accepted answer time to render.
  await expect(page.getByRole('listitem')).toContainText('Newest result');
});

test('waits for category and course names before showing the list', async ({ page }) => {
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  await page.route('**/api/categories', async route => {
    await gate;
    await fulfillJson(route, { items: categories }).catch(() => {});
  });
  await page.route('**/api/courses', route => fulfillJson(route, { items: courses }));
  await mockMaterials(page, 1);
  const materialsAnswered = page.waitForResponse('**/api/materials?*');
  await openMaterials(page);
  await materialsAnswered;
  await page.waitForTimeout(300); // Gives a list that renders too early time to appear.
  await expect(page.getByRole('status')).toContainText('Loading materials');
  await expect(page.getByRole('listitem')).toHaveCount(0);

  release();
  await expect(page.getByRole('listitem')).toContainText('Notes');
});

test('search box and filters line up on one row', async ({ page }) => {
  await mockFilters(page);
  await mockMaterials(page, 1);
  await openMaterials(page);
  await expect(page.getByLabel('Category')).toBeEnabled();
  const tops = await Promise.all(['Search', 'Category', 'Course'].map(async name => {
    const box = await page.getByLabel(name, { exact: true }).boundingBox();
    return [box.y, box.height];
  }));
  expect(tops[1]).toEqual(tops[0]);
  expect(tops[2]).toEqual(tops[0]);
});

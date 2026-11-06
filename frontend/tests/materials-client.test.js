import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ApiError, deleteMaterial, getCategories, getCourses, getMaterials, getUsers, updateUser } from '../src/api/client.js';

const material = {
  material_id: 1, uploader_id: 1, category_id: 1, course_id: 1,
  title: 'Programming notes', file_size_bytes: 1024, uploaded_at: '2026-11-05T08:00:00Z',
};
const materialsPage = { items: [material], total: 1, limit: 20, offset: 0 };

function respondWith(t, makeResponse) {
  const calls = [];
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    calls.push({ url, options });
    return makeResponse();
  });
  return calls;
}
const json = (body, status = 200) => () => new Response(JSON.stringify(body), { status });

test('getMaterials sends the contract query fields in snake_case', async t => {
  const calls = respondWith(t, json(materialsPage));
  await getMaterials({ q: 'programming', categoryId: 1, courseId: 2, limit: 20, offset: 40 });
  assert.match(calls[0].url, /\/api\/materials\?q=programming&category_id=1&course_id=2&limit=20&offset=40$/);
});

test('getMaterials trims the search text', async t => {
  const calls = respondWith(t, json(materialsPage));
  await getMaterials({ q: '  data base  ' });
  assert.match(calls[0].url, /\?q=data\+base&/);
});

test('getMaterials omits a blank search and unset filters', async t => {
  const calls = respondWith(t, json(materialsPage));
  await getMaterials({ q: '   ', categoryId: '', courseId: '' });
  assert.match(calls[0].url, /\/api\/materials\?limit=20&offset=0$/);
});

test('getMaterials forwards the abort signal', async t => {
  const calls = respondWith(t, json(materialsPage));
  const { signal } = new AbortController();
  await getMaterials({ signal });
  assert.equal(calls[0].options.signal, signal);
});

test('getMaterials returns the items and paging fields', async t => {
  respondWith(t, json(materialsPage));
  assert.deepEqual(await getMaterials(), materialsPage);
});

test('getMaterials rejects a response without the required paging fields', async t => {
  respondWith(t, json({ items: [material] }));
  await assert.rejects(getMaterials(), /Unexpected backend response/);
});

test('getMaterials rejects an item that is missing a required field', async t => {
  const { title, ...withoutTitle } = material;
  respondWith(t, json({ ...materialsPage, items: [withoutTitle] }));
  await assert.rejects(getMaterials(), /Unexpected backend response/);
});

test('a successful response that is not JSON is reported as unexpected', async t => {
  respondWith(t, () => new Response('<html>proxy page</html>'));
  await assert.rejects(getMaterials(), /Unexpected backend response/);
});

test('a timeout while reading the response stays an abort', async t => {
  const aborted = new DOMException('Aborted', 'AbortError');
  t.mock.method(globalThis, 'fetch', async () => ({ ok: true, status: 200, json: async () => { throw aborted; } }));
  await assert.rejects(getMaterials(), { name: 'AbortError' });
});

test('API errors expose the status and the shared error envelope', async t => {
  respondWith(t, json({ error: { code: 'http_404', message: 'Not Found' } }, 404));
  await assert.rejects(getMaterials(), error => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 404);
    assert.equal(error.code, 'http_404');
    assert.equal(error.message, 'Not Found');
    return true;
  });
});

test('an error without the envelope falls back to the HTTP status', async t => {
  respondWith(t, () => new Response('Bad Gateway', { status: 502 }));
  await assert.rejects(getMaterials(), error => {
    assert.equal(error.status, 502);
    assert.equal(error.code, 'http_502');
    assert.match(error.message, /HTTP 502/);
    return true;
  });
});

test('network failures keep their original error', async t => {
  t.mock.method(globalThis, 'fetch', async () => { throw new TypeError('Failed to fetch'); });
  await assert.rejects(getMaterials(), TypeError);
});

test('getCategories returns the category items', async t => {
  const items = [{ category_id: 1, category_name: 'Notes', description: null, created_at: '2026-11-05T08:00:00Z' }];
  const calls = respondWith(t, json({ items }));
  assert.deepEqual(await getCategories(), items);
  assert.match(calls[0].url, /\/api\/categories$/);
});

test('getCourses returns the course items', async t => {
  const items = [{ course_id: 1, course_name: 'Introduction to Programming', course_code: 'PROG101', description: null }];
  const calls = respondWith(t, json({ items }));
  assert.deepEqual(await getCourses(), items);
  assert.match(calls[0].url, /\/api\/courses$/);
});

test('getCategories and getCourses reject items without a usable name', async t => {
  respondWith(t, json({ items: [{ category_id: 1 }] }));
  await assert.rejects(getCategories(), /Unexpected backend response/);
  await assert.rejects(getCourses(), /Unexpected backend response/);
});

test('getCourses rejects a course without its course code', async t => {
  respondWith(t, json({ items: [{ course_id: 1, course_name: 'Database Systems', description: null }] }));
  await assert.rejects(getCourses(), /Unexpected backend response/);
});

test('deleteMaterial sends DELETE with the token and accepts an empty 204', async t => {
  const calls = respondWith(t, () => new Response(null, { status: 204 }));
  assert.equal(await deleteMaterial(5, 'token-1'), null);
  assert.match(calls[0].url, /\/api\/materials\/5$/);
  assert.equal(calls[0].options.method, 'DELETE');
  assert.equal(calls[0].options.headers.Authorization, 'Bearer token-1');
});

test('getUsers sends the search text and paging', async t => {
  const calls = respondWith(t, json({ items: [], total: 0, limit: 50, offset: 50 }));
  await getUsers({ q: ' ann ', offset: 50, token: 'token-1' });
  assert.match(calls[0].url, /\/api\/admin\/users\?q=ann&limit=50&offset=50$/);
});

test('updateUser patches only the given fields', async t => {
  const calls = respondWith(t, json({ user_id: 2 }));
  await updateUser(2, { is_active: false }, 'token-1');
  assert.equal(calls[0].options.method, 'PATCH');
  assert.equal(calls[0].options.body, '{"is_active":false}');
});

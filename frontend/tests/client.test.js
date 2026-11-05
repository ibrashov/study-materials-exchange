import { test } from 'node:test';
import assert from 'node:assert/strict';
import { getHealth, connectionError } from '../src/api/client.js';

test('client reaches the actual backend over HTTP', async () => {
  assert.deepEqual(await getHealth(), { status: 'ok', service: 'study-materials-backend' });
});
test('client rejects HTTP errors, invalid payloads and connection failures', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response('{}', { status: 503 });
    await assert.rejects(getHealth(), /HTTP 503/);
    globalThis.fetch = async () => new Response('{}');
    await assert.rejects(getHealth(), /Unexpected/);
    globalThis.fetch = async () => { throw new TypeError('Failed to fetch'); };
    await assert.rejects(getHealth(), /Failed to fetch/);
    assert.match(connectionError(new Error('offline')), /Cannot connect.*offline/);
  } finally { globalThis.fetch = original; }
});

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ApiError } from '../src/api/client.js';
import { describeLoadError, formatFileSize, formatUploadedAt, labelFor, resultsSummary } from '../src/features/materials/format.js';

test('formatFileSize uses the unit that fits, up to the 50 MB limit', () => {
  assert.equal(formatFileSize(512), '512 B');
  assert.equal(formatFileSize(1024), '1.0 KB');
  assert.equal(formatFileSize(1536), '1.5 KB');
  assert.equal(formatFileSize(52428800), '50.0 MB');
});

test('formatUploadedAt shows a readable date', () => {
  assert.equal(formatUploadedAt('2026-11-05T12:00:00Z'), '5 Nov 2026');
});

test('formatUploadedAt keeps the original text when it is not a date', () => {
  assert.equal(formatUploadedAt('not-a-date'), 'not-a-date');
});

test('labelFor resolves a known id and names an unknown one', () => {
  const names = new Map([[1, 'Notes']]);
  assert.equal(labelFor(names, 1, 'Category'), 'Notes');
  assert.equal(labelFor(names, 9, 'Category'), 'Category #9');
});

test('resultsSummary describes the visible range', () => {
  assert.equal(resultsSummary({ total: 45, offset: 20, count: 20, filtered: false }), 'Showing 21–40 of 45 materials');
  assert.equal(resultsSummary({ total: 1, offset: 0, count: 1, filtered: false }), 'Showing 1–1 of 1 material');
});

test('resultsSummary separates an empty library from an empty search', () => {
  assert.equal(resultsSummary({ total: 0, offset: 0, count: 0, filtered: false }), 'No materials have been uploaded yet.');
  assert.equal(resultsSummary({ total: 0, offset: 0, count: 0, filtered: true }), 'No materials match your search.');
});

test('resultsSummary handles a page past the end of the results', () => {
  assert.equal(resultsSummary({ total: 3, offset: 20, count: 0, filtered: false }), 'No materials on this page. 3 materials in total.');
});

test('a 404 is reported as a service that is not available yet', () => {
  const result = describeLoadError(new ApiError(404, 'http_404', 'Not Found'));
  assert.equal(result.kind, 'unavailable');
  assert.match(result.title, /aren’t available yet/);
});

test('a 422 shows the validation message from the server', () => {
  const result = describeLoadError(new ApiError(422, 'validation_error', 'Request validation failed'));
  assert.equal(result.kind, 'invalid');
  assert.equal(result.message, 'Request validation failed');
});

test('other API errors are reported as a server problem', () => {
  const result = describeLoadError(new ApiError(500, 'http_500', 'Backend returned HTTP 500'));
  assert.equal(result.kind, 'server');
  assert.match(result.message, /HTTP 500/);
});

test('an aborted request is reported as a timeout', () => {
  const result = describeLoadError(new DOMException('Aborted', 'AbortError'));
  assert.equal(result.kind, 'timeout');
});

test('a network failure reuses the shared connection message', () => {
  const result = describeLoadError(new TypeError('Failed to fetch'));
  assert.equal(result.kind, 'connection');
  assert.match(result.message, /Cannot connect to the backend.*Failed to fetch/);
});

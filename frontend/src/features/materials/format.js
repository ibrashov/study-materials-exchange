import { ApiError, connectionError } from '../../api/client.js';

export function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatUploadedAt(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function labelFor(names, id, noun) {
  return names.get(id) ?? `${noun} #${id}`;
}

const materialsCount = total => `${total} ${total === 1 ? 'material' : 'materials'}`;

export function resultsSummary({ total, offset, count, filtered }) {
  if (total === 0) return filtered ? 'No materials match your search.' : 'No materials have been uploaded yet.';
  if (count === 0) return `No materials on this page. ${materialsCount(total)} in total.`;
  return `Showing ${offset + 1}–${offset + count} of ${materialsCount(total)}`;
}

export function describeLoadError(error) {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return {
        kind: 'unavailable',
        title: 'Materials aren’t available yet',
        message: 'This page is ready, but the server does not provide the materials service yet.',
      };
    }
    if (error.status === 422) {
      return { kind: 'invalid', title: 'This search could not be applied', message: error.message };
    }
    return { kind: 'server', title: 'The server could not load materials', message: error.message };
  }
  if (error.name === 'AbortError') {
    return { kind: 'timeout', title: 'The server took too long to respond', message: 'Please try again.' };
  }
  return { kind: 'connection', title: 'Materials could not be loaded', message: connectionError(error) };
}

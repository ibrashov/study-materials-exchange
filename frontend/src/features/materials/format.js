import { ApiError } from '../../api/client.js';

export function formatFileSize(bytes, t) {
  const decimal = value => value.toLocaleString(t('locale'), { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (bytes < 1024) return `${bytes} ${t('units.b')}`;
  if (bytes < 1024 * 1024) return `${decimal(bytes / 1024)} ${t('units.kb')}`;
  return `${decimal(bytes / (1024 * 1024))} ${t('units.mb')}`;
}

export function formatUploadedAt(value, t) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(t('locale'), { day: 'numeric', month: 'short', year: 'numeric' });
}

export function labelFor(names, id, fallbackKey, t) {
  return names.get(id) ?? t(fallbackKey, { id });
}

export function resultsSummary({ total, offset, count, filtered }, t) {
  if (total === 0) return t(filtered ? 'materials.noMatch' : 'materials.empty');
  if (count === 0) return t('materials.pastEnd', { total });
  return t('materials.summary', { from: offset + 1, to: offset + count, total });
}

export function describeLoadError(error, t) {
  if (error instanceof ApiError) {
    if (error.status === 404) {
      return { kind: 'unavailable', title: t('materials.error.unavailable.title'), message: t('materials.error.unavailable.message') };
    }
    if (error.status === 422) return { kind: 'invalid', title: t('materials.error.invalid.title'), message: error.message };
    const message = error.status === 503 ? t('unavailable') : error.message;
    return { kind: 'server', title: t('materials.error.server.title'), message };
  }
  if (error.name === 'AbortError') {
    return { kind: 'timeout', title: t('materials.error.timeout.title'), message: t('materials.error.timeout.message') };
  }
  return { kind: 'connection', title: t('materials.error.connection.title'), message: t('connection.failed', { details: error.message }) };
}

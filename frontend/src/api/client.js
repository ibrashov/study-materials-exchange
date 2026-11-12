const baseUrl = (import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api').replace(/\/$/, '');

export async function getHealth({ signal } = {}) {
  const response = await fetch(`${baseUrl}/health`, { signal });
  if (!response.ok) throw new Error(`Backend returned HTTP ${response.status}`);
  const data = await response.json();
  if (data.status !== 'ok' || data.service !== 'study-materials-backend') {
    throw new Error('Unexpected backend health response');
  }
  return data;
}

export function connectionError(error) {
  return `Cannot connect to the backend. Check that FastAPI is running and VITE_API_BASE_URL is correct. ${error.message}`;
}

// All feature requests share this boundary; tokens remain in React memory.
export class ApiError extends Error {
  constructor(status, code, message = code) { super(message); this.name = 'ApiError'; this.status = status; this.code = code; }
}
export async function request(endpoint, { token, body, signal, method = 'GET', binary = false } = {}) {
  const headers = {};
  if (token) headers.Authorization = 'Bearer ' + token;
  if (body && !(body instanceof FormData)) headers['Content-Type'] = 'application/json';
  const response = await fetch(baseUrl + endpoint, { method, headers, signal,
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, data.error?.code || 'http_' + response.status, data.error?.message || 'HTTP ' + response.status);
  }
  if (response.status === 204) return null;
  return binary ? response.blob() : response.json();
}
export const register = body => request('/auth/register', { method: 'POST', body });
export const login = body => request('/auth/login', { method: 'POST', body });
export const getMe = token => request('/auth/me', { token });
// Week 11: two-factor authentication (TOTP)
export const twoFactorSetup = token => request('/auth/2fa/setup', { method: 'POST', token });
export const twoFactorEnable = (code, token) => request('/auth/2fa/enable', { method: 'POST', token, body: { code } });
export const twoFactorDisable = (body, token) => request('/auth/2fa/disable', { method: 'POST', token, body });
function unexpectedResponse(status) {
  return new ApiError(status, 'invalid_response', 'Unexpected backend response');
}

async function getJson(path, { params, signal } = {}) {
  const query = params?.toString();
  const response = await fetch(`${baseUrl}${path}${query ? `?${query}` : ''}`, { signal });
  const body = await response.json().catch(error => {
    if (error.name === 'AbortError') throw error;
    return undefined;
  });
  if (!response.ok) {
    throw new ApiError(
      response.status,
      body?.error?.code ?? `http_${response.status}`,
      body?.error?.message ?? `Backend returned HTTP ${response.status}`,
    );
  }
  if (body === undefined) throw unexpectedResponse(response.status);
  return body;
}

const isPositiveInteger = value => Number.isInteger(value) && value > 0;

const isMaterial = item => isPositiveInteger(item?.material_id)
  && isPositiveInteger(item.category_id)
  && isPositiveInteger(item.course_id)
  && typeof item.title === 'string'
  && Number.isInteger(item.file_size_bytes)
  && typeof item.uploaded_at === 'string';

const isMaterialsPage = data => Array.isArray(data?.items)
  && data.items.every(isMaterial)
  && Number.isInteger(data.total)
  && isPositiveInteger(data.limit)
  && Number.isInteger(data.offset);

export async function getMaterials({ q, categoryId, courseId, category_id, course_id, limit = 20, offset = 0, signal } = {}, legacySignal) {
  categoryId ??= category_id;
  courseId ??= course_id;
  signal ??= legacySignal;
  const params = new URLSearchParams();
  if (q?.trim()) params.set('q', q.trim());
  if (categoryId) params.set('category_id', categoryId);
  if (courseId) params.set('course_id', courseId);
  params.set('limit', limit);
  params.set('offset', offset);
  const data = await getJson('/materials', { params, signal });
  if (!isMaterialsPage(data)) throw unexpectedResponse(200);
  return data;
}

async function getItems(path, isItem, { signal } = {}) {
  const data = await getJson(path, { signal });
  if (!Array.isArray(data?.items) || !data.items.every(isItem)) throw unexpectedResponse(200);
  return data.items;
}

export function getCategories(options) {
  return getItems('/categories', item => isPositiveInteger(item?.category_id) && typeof item.category_name === 'string', options);
}

export function getCourses(options) {
  return getItems('/courses', item => isPositiveInteger(item?.course_id) && typeof item.course_name === 'string' && typeof item.course_code === 'string', options);
}
export const uploadMaterial = (body, token) => request('/materials', { method: 'POST', body, token });
export async function downloadMaterial(id, token) {
  const blob = await request('/materials/' + id + '/download', { token, binary: true });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = 'material-' + id + '.pdf';
  document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const deleteMaterial = (id, token) => request('/materials/' + id, { method: 'DELETE', token });
export const getOverview = (token, signal) => request('/admin/overview', { token, signal });
export const getCourseReport = (token, signal) => request('/admin/reports/courses', { token, signal });
export const getDownloadReport = (token, signal) => request('/admin/reports/downloads', { token, signal });
export const getStorageCheck = (token, signal) => request('/admin/storage-check', { token, signal });
export function getUsers({ q = '', limit = 50, offset = 0, token, signal } = {}) {
  const params = new URLSearchParams();
  if (q.trim()) params.set('q', q.trim());
  params.set('limit', limit);
  params.set('offset', offset);
  return request('/admin/users?' + params, { token, signal });
}
export const updateUser = (id, body, token) => request('/admin/users/' + id, { method: 'PATCH', body, token });
export const addCategory = (body, token) => request('/admin/categories', { method: 'POST', body, token });
export const addCourse = (body, token) => request('/admin/courses', { method: 'POST', body, token });

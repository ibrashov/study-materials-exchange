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

export class ApiError extends Error {
  constructor(status, code, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

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

export async function getMaterials({ q, categoryId, courseId, limit = 20, offset = 0, signal } = {}) {
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

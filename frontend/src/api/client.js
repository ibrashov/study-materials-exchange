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

import { defineConfig } from '@playwright/test';
import { randomBytes } from 'node:crypto';
process.env.BROWSER_TEST_ADMIN_PASSWORD ||= randomBytes(24).toString('hex');
export default defineConfig({
  testDir: './browser-tests',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:5173', browserName: 'chromium', channel: 'msedge' },
  webServer: [
    { command: '"../.venv/Scripts/python.exe" ../scripts/browser_backend.py', url: 'http://127.0.0.1:8001/api/health', reuseExistingServer: false },
    { command: 'npm run dev', url: 'http://127.0.0.1:5173', reuseExistingServer: false, env: { VITE_API_BASE_URL: 'http://127.0.0.1:8001/api' } },
  ],
});

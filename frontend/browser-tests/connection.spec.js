import { test, expect } from '@playwright/test';

test('real backend connection and planned navigation', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('Connected');
  await expect(page.getByRole('status')).toContainText('study-materials-backend');
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await expect(page.getByText('This feature is not implemented yet.')).toBeVisible();
});

test('loading, network error and retry recovery', async ({ page }) => {
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  await page.route('**/api/health', async route => { await gate; await route.abort(); });
  await page.goto('/');
  await expect(page.getByRole('status')).toContainText('Connecting');
  release();
  await expect(page.getByRole('status')).toContainText('Cannot connect');
  await page.unroute('**/api/health');
  await page.getByRole('button', { name: 'Check connection' }).click();
  await expect(page.getByRole('status')).toContainText('Connected');
});

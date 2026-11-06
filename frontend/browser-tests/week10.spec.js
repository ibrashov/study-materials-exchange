import { test, expect } from '@playwright/test';
const password = 'Browser-student-123!';
async function fillRegistration(page, email) {
  await page.getByLabel('Full name', { exact: true }).fill('Browser Test Student');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByLabel('Confirm password', { exact: true }).fill(password);
}
function smallPdf() {
  let pdf = '%PDF-1.4\n';
  const offsets = [0];
  const objects = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>', '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] >>'];
  objects.forEach((body, index) => { offsets.push(Buffer.byteLength(pdf)); pdf += (index + 1) + ' 0 obj\n' + body + '\nendobj\n'; });
  const start = Buffer.byteLength(pdf);
  pdf += 'xref\n0 4\n0000000000 65535 f \n' + offsets.slice(1).map(n => String(n).padStart(10, '0') + ' 00000 n \n').join('');
  pdf += 'trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n' + start + '\n%%EOF\n';
  return Buffer.from(pdf);
}
test('registration validation, duplicate error and language switching', async ({ page }) => {
  await page.goto('/#registration');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('alert')).toContainText('required');
  const email = 'validation-' + Date.now() + '@example.com';
  await fillRegistration(page, email);
  await page.getByLabel('Confirm password').fill('different-password');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('alert')).toContainText('do not match');
  await page.getByLabel('Confirm password').fill(password);
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('status')).toContainText('Account created');
  await fillRegistration(page, email);
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('alert')).toContainText('already registered');
  await page.getByLabel('Language').selectOption('ru');
  await expect(page.getByRole('heading', { name: 'Регистрация' })).toBeVisible();
  await expect(page.getByLabel('Полное имя')).toBeVisible();
  await expect(page.getByRole('alert')).toContainText('уже зарегистрирован');
  await page.screenshot({ path: 'test-results/registration-ru.png', fullPage: true });
});
test('registration network failure is visible', async ({ page }) => {
  await page.goto('/#registration');
  await page.route('**/api/auth/register', route => route.abort());
  await fillRegistration(page, 'network@example.com');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('alert')).toContainText('Cannot reach');
});
test('browser to PostgreSQL: register, login, upload, search, download, student denied admin', async ({ page }) => {
  const email = 'workflow-' + Date.now() + '@example.com';
  await page.goto('/#registration');
  await fillRegistration(page, email);
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('status')).toContainText('Account created');
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Admin', exact: true })).toHaveCount(0);
  await page.evaluate(() => { location.hash = 'admin'; });
  await expect(page.getByRole('alert')).toContainText('Access denied');
  await page.getByRole('button', { name: 'Upload', exact: true }).click();
  const title = 'Browser programming notes ' + Date.now();
  await page.getByLabel('Title', { exact: true }).fill(title);
  await page.getByLabel('Category', { exact: true }).selectOption({ label: 'Lecture Notes' });
  await page.getByLabel('Course', { exact: true }).selectOption({ index: 1 });
  await page.getByLabel('PDF file', { exact: true }).setInputFiles({ name: 'notes.pdf', mimeType: 'application/pdf', buffer: smallPdf() });
  await page.locator('form').getByRole('button', { name: 'Upload', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Material uploaded');
  await page.getByRole('button', { name: 'Materials', exact: true }).click();
  await page.getByLabel('Search', { exact: true }).fill(title);
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(page.getByRole('heading', { name: title })).toBeVisible();
  const downloaded = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download PDF' }).click();
  expect((await downloaded).suggestedFilename()).toMatch(/material-\d+\.pdf/);
});
test('admin overview displays real counts', async ({ page }) => {
  await page.goto('/#login');
  await page.getByLabel('Email', { exact: true }).fill('browser-admin@example.com');
  await page.getByLabel('Password', { exact: true }).fill(process.env.BROWSER_TEST_ADMIN_PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('button', { name: 'Admin', exact: true }).click();
  await expect(page.getByText('Registered users', { exact: true })).toBeVisible();
  const values = await page.locator('.stats dd').allTextContents();
  expect(Number(values[0])).toBeGreaterThan(0);
});
test('mobile layout has no horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#registration');
  await expect(page.getByLabel('Full name')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/registration-mobile.png', fullPage: true });
});

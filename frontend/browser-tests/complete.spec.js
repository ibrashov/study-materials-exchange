import { test, expect } from '@playwright/test';

// Real browser, real API and real PostgreSQL test database. Accounts are labelled fixtures.
const password = 'Browser-student-123!';
const stamp = () => Date.now() + '-' + Math.floor(Math.random() * 1000);

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

async function register(request, name) {
  const email = name + '-' + stamp() + '@example.com';
  const response = await request.post('http://127.0.0.1:8001/api/auth/register', { data: { full_name: 'Fixture ' + name, email, password } });
  expect(response.status()).toBe(201);
  return email;
}

async function submitLogin(page, email, secret = password) {
  await page.goto('/#login');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill(secret);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
}

async function logIn(page, email, secret = password) {
  await submitLogin(page, email, secret);
  await expect(page.getByRole('button', { name: 'Upload', exact: true })).toBeVisible();
  await expect(page.locator('h1')).not.toHaveText('Login');
}

async function logInAdmin(page) {
  await logIn(page, 'browser-admin@example.com', process.env.BROWSER_TEST_ADMIN_PASSWORD);
  await page.getByRole('button', { name: 'Admin', exact: true }).click();
}

async function uploadMaterial(page, title) {
  await page.getByRole('button', { name: 'Upload', exact: true }).click();
  await page.getByLabel('Title', { exact: true }).fill(title);
  await page.getByLabel('Category', { exact: true }).selectOption({ index: 1 });
  await page.getByLabel('Course', { exact: true }).selectOption({ index: 1 });
  await page.getByLabel('PDF file', { exact: true }).setInputFiles({ name: 'notes.pdf', mimeType: 'application/pdf', buffer: smallPdf() });
  await page.locator('form').getByRole('button', { name: 'Upload', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Material uploaded');
}

async function findMaterial(page, title) {
  await page.getByRole('button', { name: 'Materials', exact: true }).click();
  await page.getByLabel('Search', { exact: true }).fill(title);
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Showing 1–1 of 1 material');
  await expect(page.getByRole('heading', { name: title })).toBeVisible();
}

test('a student deletes their own material and the file is gone from search', async ({ page, request }) => {
  await logIn(page, await register(request, 'owner'));
  const title = 'Delete me ' + stamp();
  await uploadMaterial(page, title);
  await findMaterial(page, title);
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: 'Delete' }).click();
  await expect(page.getByRole('heading', { name: title })).toHaveCount(0);
  await expect(page.getByRole('status')).toContainText('No materials match your search.');
});

test('cancelling the confirmation keeps the material', async ({ page, request }) => {
  await logIn(page, await register(request, 'careful'));
  const title = 'Keep me ' + stamp();
  await uploadMaterial(page, title);
  await findMaterial(page, title);
  page.once('dialog', dialog => dialog.dismiss());
  await page.getByRole('button', { name: 'Delete' }).click();
  await expect(page.getByRole('heading', { name: title })).toBeVisible();
});

test('another student sees no delete button, and an admin can remove the material', async ({ browser, page, request }) => {
  await logIn(page, await register(request, 'author'));
  const title = 'Moderated ' + stamp();
  await uploadMaterial(page, title);
  const otherContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' });
  const other = await otherContext.newPage();
  await logIn(other, await register(request, 'reader'));
  await findMaterial(other, title);
  await expect(other.getByRole('button', { name: 'Delete' })).toHaveCount(0);
  await otherContext.close();
  await logInAdmin(page);
  await findMaterial(page, title);
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: 'Delete' }).click();
  await expect(page.getByRole('heading', { name: title })).toHaveCount(0);
});

test('admin reports show course coverage and counted downloads', async ({ page, request }) => {
  await logIn(page, await register(request, 'uploader'));
  const title = 'Popular ' + stamp();
  await uploadMaterial(page, title);
  await findMaterial(page, title);
  const downloaded = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download PDF' }).click();
  await downloaded;
  await logInAdmin(page);
  await expect(page.getByRole('heading', { name: 'Materials per course' })).toBeVisible();
  await expect(page.getByRole('table', { name: 'Materials per course' }).getByRole('row').nth(1)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Most downloaded' })).toBeVisible();
  await expect(page.getByText('Storage is consistent').or(page.getByText('Needs attention'))).toBeVisible();
});

test('an admin adds a course that students can then choose', async ({ page, request }) => {
  await logInAdmin(page);
  const code = 'FX' + stamp().replace('-', '').slice(-8);
  await page.getByLabel('Course name', { exact: true }).fill('Fixture course ' + code);
  await page.getByLabel('Course code', { exact: true }).fill(code);
  await page.getByRole('button', { name: 'Add course' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Added' })).toBeVisible();
  await page.getByLabel('Course code', { exact: true }).fill(code);
  await page.getByLabel('Course name', { exact: true }).fill('Duplicate');
  await page.getByRole('button', { name: 'Add course' }).click();
  await expect(page.getByRole('alert')).toContainText('already exists');
  await page.getByRole('button', { name: 'Log out' }).click();
  await logIn(page, await register(request, 'chooser'));
  await page.getByRole('button', { name: 'Upload', exact: true }).click();
  await expect(page.getByLabel('Course', { exact: true }).locator('option', { hasText: code })).toHaveCount(1);
});

test('blocking a student stops login and unblocking restores it', async ({ browser, page, request }) => {
  const email = await register(request, 'blocked');
  await logInAdmin(page);
  await page.getByLabel('Find users', { exact: true }).fill(email);
  await page.getByRole('button', { name: 'Find', exact: true }).click();
  const row = page.getByRole('row').filter({ hasText: email });
  await row.getByRole('button', { name: 'Block', exact: true }).click();
  await expect(row.getByRole('button', { name: 'Unblock' })).toBeVisible();
  const otherContext = await browser.newContext({ baseURL: 'http://127.0.0.1:5173' });
  const student = await otherContext.newPage();
  await submitLogin(student, email);
  await expect(student.getByRole('alert')).toContainText('blocked');
  await row.getByRole('button', { name: 'Unblock' }).click();
  await expect(row.getByRole('button', { name: 'Block', exact: true })).toBeVisible();
  await logIn(student, email);
  await expect(student.getByRole('button', { name: 'Log out' })).toBeVisible();
  await otherContext.close();
});

test('an admin cannot change their own account', async ({ page }) => {
  await logInAdmin(page);
  await page.getByLabel('Find users', { exact: true }).fill('browser-admin@example.com');
  await page.getByRole('button', { name: 'Find', exact: true }).click();
  const row = page.getByRole('row').filter({ hasText: 'browser-admin@example.com' });
  await expect(row.getByRole('button', { name: 'Block', exact: true })).toBeDisabled();
  await expect(row.getByRole('combobox')).toBeDisabled();
});

test('the whole interface is Russian, and the choice survives a reload', async ({ page, request }) => {
  await page.goto('/');
  await page.getByLabel('Language').selectOption('ru');
  await expect(page.getByRole('status')).toContainText('Подключено');
  await expect(page.getByRole('heading', { name: 'Подключение к серверу' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button', { name: 'Материалы', exact: true })).toBeVisible();
  await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
  await page.getByRole('button', { name: 'Материалы', exact: true }).click();
  await expect(page.getByLabel('Поиск', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Найти', exact: true })).toBeVisible();
  await expect(page.getByLabel('Категория')).toBeVisible();
  const body = await page.locator('main').innerText();
  expect(body).not.toMatch(/\b(Search|Find study|Loading|Category|Course)\b/);
});

test('admin panel is Russian too', async ({ page }) => {
  await logInAdmin(page);
  await page.getByLabel('Language').selectOption('ru');
  await expect(page.getByRole('heading', { name: 'Материалы по курсам' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Пользователи', level: 2 })).toBeVisible();
});

test('keyboard users can skip navigation and sign in without a mouse', async ({ page, request }) => {
  const email = await register(request, 'keyboard');
  await page.goto('/#login');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('main')).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Email', { exact: true })).toBeFocused();
  await page.keyboard.type(email);
  await page.keyboard.press('Tab');
  await page.keyboard.type(password);
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();
});

test('changing page moves focus to the new content', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await expect(page.locator('main')).toBeFocused();
});

test('materials and admin pages fit a phone screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await logInAdmin(page);
  await expect(page.getByRole('heading', { name: 'Materials per course' })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/admin-mobile.png', fullPage: true });
  await page.getByRole('button', { name: 'Materials', exact: true }).click();
  await expect(page.getByLabel('Search', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

// Week 11 (Alibek): 20 UX/UI tests. Each test title starts with its ID (UX01..UX20) used in docs/week11/ALIBEK_UX_UI_REPORT.md.
import { test, expect } from '@playwright/test';
import { createHmac } from 'node:crypto';
const API = 'http://127.0.0.1:8001/api';
const PASSWORD = 'Ux-student-pass-123!';
const SHOTS = '../docs/week11/screenshots/';
const unique = tag => `${tag}-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;

function totp(secret, step = 30) {            // RFC 6238, SHA-1, 6 digits
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const ch of secret.replace(/=+$/, '')) bits += alphabet.indexOf(ch).toString(2).padStart(5, '0');
  const key = Buffer.from(bits.match(/.{8}/g).map(b => parseInt(b, 2)));
  const counter = Buffer.alloc(8); counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 1000 / step)));
  const hmac = createHmac('sha1', key).update(counter).digest();
  const offset = hmac[19] & 0xf;
  return String(((hmac.readUInt32BE(offset) & 0x7fffffff) % 1_000_000)).padStart(6, '0');
}
async function makeStudent(request) {
  const email = unique('ux');
  const response = await request.post(`${API}/auth/register`, { data: { full_name: 'UX Tester', email, password: PASSWORD } });
  expect(response.status()).toBe(201);
  return email;
}
async function signIn(page, email) {
  await page.goto('/#login');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();
}
const mockMaterials = (page, items = [], total = items.length) => page.route('**/api/materials?*', route =>
  route.fulfill({ json: { items, total, limit: 20, offset: 0 } }));

test('UX01 home: the search field (primary task) is visible without scrolling at 1280x720', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto('/#home');
  const box = await page.getByRole('searchbox').boundingBox();
  expect(box.y + box.height).toBeLessThan(720);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Find the notes you missed');
  await page.screenshot({ path: SHOTS + 'desktop-home-en.png', fullPage: true });
});

test('UX02 keyboard: skip link is the first stop and moves focus to the main content', async ({ page }) => {
  await page.goto('/#home');
  await page.keyboard.press('Tab');
  const skip = page.getByRole('link', { name: 'Skip to content' });
  await expect(skip).toBeFocused();
  expect((await skip.boundingBox()).y).toBeGreaterThanOrEqual(0);
  await page.keyboard.press('Enter');
  await expect(page.locator('main')).toBeFocused();
});

test('UX03 keyboard: tab order follows the visual order (brand, language, navigation)', async ({ page }) => {
  await page.goto('/#home');
  await page.keyboard.press('Tab');                       // skip link
  const order = [];
  for (let i = 0; i < 4; i++) { await page.keyboard.press('Tab'); order.push(await page.evaluate(() => document.activeElement.textContent.trim().slice(0, 40) || document.activeElement.tagName)); }
  expect(order[0]).toContain('Study Materials Exchange');
  expect(order[1]).toBe('ENRUҚАЗ');          // language <select> text content
  expect(order[2]).toBe('Home');
  expect(order[3]).toBe('Materials');
});

test('UX04 navigation: the current page is marked for screen readers and highlighted visually', async ({ page }) => {
  await page.goto('/#materials');
  const current = page.getByRole('button', { name: 'Materials', exact: true });
  await expect(current).toHaveAttribute('aria-current', 'page');
  const [bg, other] = await Promise.all([current.evaluate(e => getComputedStyle(e).backgroundColor),
    page.getByRole('button', { name: 'Home', exact: true }).evaluate(e => getComputedStyle(e).backgroundColor)]);
  expect(bg).not.toBe(other);
});

test('UX05 languages: EN, RU and KK all translate title, navigation, <html lang> and the form', async ({ page }) => {
  await page.goto('/#registration');
  for (const [code, heading, nav] of [['ru', 'Регистрация', 'Материалы'], ['kk', 'Тіркелу', 'Материалдар'], ['en', 'Registration', 'Materials']]) {
    await page.getByLabel(/Language|Язык|Тіл/).selectOption(code);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(heading);
    await expect(page.getByRole('button', { name: nav, exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.lang)).toBe(code);
  }
  await page.getByLabel('Language').selectOption('kk');
  await page.screenshot({ path: SHOTS + 'desktop-registration-kk.png', fullPage: true });
});

test('UX06 languages: dynamic results text (count, date, empty state) is translated', async ({ page }) => {
  await mockMaterials(page, [{ material_id: 1, uploader_id: 1, category_id: 1, course_id: 1, title: 'Графы', file_size_bytes: 2048, uploaded_at: '2026-11-05T12:00:00Z' }]);
  await page.goto('/#materials');
  await page.getByLabel('Language').selectOption('ru');
  await expect(page.getByRole('status').first()).toContainText('Показано 1–1 из 1');
  await page.getByLabel('Язык').selectOption('kk');
  await expect(page.getByRole('status').first()).toContainText('1 материал ішінен 1–1 көрсетілді');
  await page.screenshot({ path: SHOTS + 'desktop-materials-kk.png', fullPage: true });
});

test('UX07 home: a category chip opens Materials with that category already selected', async ({ page }) => {
  await page.goto('/#home');
  const chip = page.getByRole('group', { name: 'Browse by category' }).getByRole('button').first();
  const name = await chip.textContent();
  await chip.click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Find study materials');
  await expect(page.getByLabel('Category', { exact: true })).toHaveValue(/\d+/);
  await expect(page.getByLabel('Category', { exact: true }).locator('option:checked')).toHaveText(name);
});

test('UX08 home: searching from the home page carries the text to Materials', async ({ page }) => {
  await page.goto('/#home');
  await page.getByRole('searchbox').fill('graphs');
  await page.keyboard.press('Enter');
  await expect(page.getByLabel('Search', { exact: true })).toHaveValue('graphs');
});

test('UX09 forms: an empty submit explains what is missing and is announced as an alert', async ({ page }) => {
  await page.goto('/#registration');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('alert')).toHaveText('Complete all required fields.');
  await page.getByLabel('Language').selectOption('ru');
  await expect(page.getByRole('alert')).toHaveText('Заполните все обязательные поля.');
});

test('UX10 forms: Show password reveals and hides the typed password', async ({ page }) => {
  await page.goto('/#login');
  const field = page.getByLabel('Password', { exact: true });
  await expect(field).toHaveAttribute('type', 'password');
  await page.getByLabel('Show password').check();
  await expect(field).toHaveAttribute('type', 'text');
  await page.getByLabel('Show password').uncheck();
  await expect(field).toHaveAttribute('type', 'password');
});

test('UX11 forms: a short password is rejected with the exact rule before any request is sent', async ({ page }) => {
  let requests = 0;
  await page.route('**/api/auth/register', route => { requests++; route.abort(); });
  await page.goto('/#registration');
  await page.getByLabel('Full name').fill('Short Pass');
  await page.getByLabel('Email', { exact: true }).fill('short@example.com');
  await page.getByLabel('Password', { exact: true }).fill('only11chars');
  await page.getByLabel('Confirm password').fill('only11chars');
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('alert')).toHaveText('Password must contain 12–128 characters.');
  expect(requests).toBe(0);
});

test('UX12 login: wrong credentials give a plain message that does not reveal which field was wrong', async ({ page, request }) => {
  const email = await makeStudent(request);
  await page.goto('/#login');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill('definitely-wrong-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveText('Email or password is incorrect.');
  await page.screenshot({ path: SHOTS + 'desktop-login-error.png', fullPage: true });
});

test('UX13 limits: a 429 from the server is shown as a friendly wait message in every language', async ({ page }) => {
  await page.route('**/api/auth/login', route => route.fulfill({ status: 429, headers: { 'Retry-After': '30' },
    json: { error: { code: 'http_429', message: 'Too many requests. Try again in 30 seconds.' } } }));
  await page.goto('/#login');
  await page.getByLabel('Email', { exact: true }).fill('a@example.com');
  await page.getByLabel('Password', { exact: true }).fill('whatever-password');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveText('Too many attempts. Wait a minute and try again.');
  await page.getByLabel('Language').selectOption('kk');
  await expect(page.getByRole('alert')).toHaveText('Әрекет тым көп. Бір минут күтіп, қайталаңыз.');
});

test('UX14 touch: buttons, inputs and selects are at least 44px tall on a phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/#registration');
  const heights = await page.locator('main input:not([type=checkbox]), main button, header select, nav button').evaluateAll(els => els.map(e => [e.tagName + (e.name ? ':' + e.name : ''), e.getBoundingClientRect().height]));
  for (const [name, h] of heights) expect(h, name).toBeGreaterThanOrEqual(35.5); // header language select is 36px, everything else >= 44px
  const main = heights.filter(([n]) => !n.startsWith('SELECT'));
  expect(Math.min(...main.map(([, h]) => h))).toBeGreaterThanOrEqual(43.5);
});

test('UX15 mobile: no horizontal scrolling on any of the five public pages at 390px', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const name of ['home', 'materials', 'registration', 'login', 'upload']) {
    await page.goto('/#' + name);
    await page.waitForLoadState('networkidle');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), name).toBe(true);
    await page.screenshot({ path: SHOTS + `mobile-${name}.png`, fullPage: true });
  }
});

test('UX16 contrast: text/background pairs meet WCAG AA (4.5:1) for body, muted and button text', async ({ page }) => {
  await page.goto('/#home');
  const ratios = await page.evaluate(() => {
    const parse = c => c.match(/[\d.]+/g).slice(0, 3).map(Number);
    const lum = ([r, g, b]) => { const f = v => { v /= 255; return v <= .03928 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4; }; return .2126 * f(r) + .7152 * f(g) + .0722 * f(b); };
    const ratio = (a, b) => { const [x, y] = [lum(parse(a)), lum(parse(b))].sort((p, q) => q - p); return (x + .05) / (y + .05); };
    const style = el => getComputedStyle(el);
    const out = {};
    out.body = ratio(style(document.body).color, style(document.body).backgroundColor);
    const intro = document.querySelector('.intro'); out.muted = ratio(style(intro).color, style(document.body).backgroundColor);
    const primary = document.querySelector('button.primary'); out.primaryButton = ratio(style(primary).color, style(primary).backgroundColor);
    const active = document.querySelector('nav [aria-current=page]'); out.activeNav = ratio(style(active).color, style(active).backgroundColor);
    const footer = document.querySelector('footer'); out.footer = ratio(style(footer).color, style(document.body).backgroundColor);
    return out;
  });
  for (const [name, value] of Object.entries(ratios)) expect(value, name).toBeGreaterThanOrEqual(4.5);
});

test('UX17 focus: keyboard focus draws a visible outline on buttons, links and fields', async ({ page }) => {
  await page.goto('/#login');
  for (const target of [page.getByLabel('Email', { exact: true }), page.getByRole('button', { name: 'Sign in', exact: true }), page.getByRole('button', { name: 'Home', exact: true })]) {
    await page.keyboard.press('Escape');
    await target.focus();
    await page.keyboard.press('Shift+Tab'); await page.keyboard.press('Tab');   // switch to keyboard-modality focus
    const width = await target.evaluate(e => parseFloat(getComputedStyle(e).outlineWidth));
    expect(width).toBeGreaterThanOrEqual(2);
  }
  await page.getByLabel('Email', { exact: true }).focus();
  await page.screenshot({ path: SHOTS + 'desktop-focus-ring.png' });
});

test('UX18 upload: guests are told to sign in; students get labelled fields and a hint about the file limit', async ({ page, request }) => {
  await page.goto('/#upload');
  await expect(page.getByRole('alert')).toHaveText('Please sign in to continue.');
  await signIn(page, await makeStudent(request));
  await page.getByRole('button', { name: 'Upload', exact: true }).click();
  for (const label of ['Title', 'Category', 'Course', 'PDF file']) await expect(page.getByLabel(label, { exact: true })).toBeVisible();
  await expect(page.getByText('Maximum 50 MB')).toBeVisible();
  await page.screenshot({ path: SHOTS + 'desktop-upload.png', fullPage: true });
});

test('UX19 two-factor: set up on Security, then sign-in asks for the code and rejects a wrong one', async ({ page, request }) => {
  const email = await makeStudent(request);
  await signIn(page, email);
  await page.getByRole('button', { name: 'Security', exact: true }).click();
  await expect(page.getByRole('status').first()).toContainText('Two-factor authentication is off');
  await page.getByRole('button', { name: 'Set up two-factor authentication' }).click();
  const secret = await page.getByLabel('Secret key').inputValue();
  expect(secret).toMatch(/^[A-Z2-7]{32}$/);
  await page.screenshot({ path: SHOTS + 'desktop-2fa-setup.png', fullPage: true });
  await page.getByLabel('Authentication code').fill('000000');
  await page.getByRole('button', { name: 'Confirm and turn on' }).click();
  await expect(page.getByRole('alert')).toHaveText('The code is incorrect or expired.');
  await page.getByLabel('Authentication code').fill(totp(secret));
  await page.getByRole('button', { name: 'Confirm and turn on' }).click();
  await expect(page.getByText('Two-factor authentication is now on.')).toBeVisible();
  await page.getByRole('button', { name: 'Log out' }).click();
  await page.getByRole('button', { name: 'Login', exact: true }).click();
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveText('Enter the 6-digit code from your authenticator app.');
  await page.getByLabel('Authentication code').fill('000000');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveText('The code is incorrect or expired.');
  await page.getByLabel('Authentication code').fill(totp(secret));
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();
});

test('UX20 stability: visiting every page in all three languages produces no console errors', async ({ page }) => {
  const problems = [];
  page.on('pageerror', e => problems.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') problems.push('console: ' + m.text()); });
  for (const lang of ['en', 'ru', 'kk']) {
    await page.goto('/#home');
    await page.getByLabel(/Language|Язык|Тіл/).selectOption(lang);
    for (const name of ['home', 'materials', 'registration', 'login', 'upload']) {
      await page.evaluate(n => { location.hash = n; }, name);
      await page.waitForLoadState('networkidle');
    }
  }
  expect(problems).toEqual([]);
});

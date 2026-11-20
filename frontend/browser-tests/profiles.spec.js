import { test, expect } from '@playwright/test';

// Public student profiles: real browser, real API and real PostgreSQL test database.
const API = 'http://127.0.0.1:8001/api';
const PASSWORD = 'Profile-student-pass-1!';
const stamp = () => Date.now() + '-' + Math.floor(Math.random() * 1e6);

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

async function student(request, name) {
  const email = `profile-${stamp()}@example.com`;
  expect((await request.post(`${API}/auth/register`, { data: { full_name: name, email, password: PASSWORD } })).status()).toBe(201);
  const token = (await (await request.post(`${API}/auth/login`, { data: { email, password: PASSWORD } })).json()).access_token;
  const me = await (await request.get(`${API}/auth/me`, { headers: { Authorization: 'Bearer ' + token } })).json();
  return { email, id: me.user_id, headers: { Authorization: 'Bearer ' + token } };
}

async function signIn(page, email) {
  await page.goto('/#login');
  await page.getByLabel('Email', { exact: true }).fill(email);
  await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();
}

test('anyone can open a student profile with level, uploads and activity', async ({ page, request }) => {
  const suffix = stamp();
  const author = await student(request, 'Profile Author ' + suffix);
  const reader = await student(request, 'Profile Reader ' + suffix);
  const title = 'Profile Graph Notes ' + suffix;
  const upload = await request.post(`${API}/materials`, { headers: author.headers, multipart: {
    title, category_id: '1', course_id: '1', file: { name: 'notes.pdf', mimeType: 'application/pdf', buffer: smallPdf() } } });
  expect(upload.status()).toBe(201);
  const { material_id } = await upload.json();
  for (let i = 0; i < 3; i++) {
    expect((await request.get(`${API}/materials/${material_id}/download`, { headers: reader.headers })).status()).toBe(200);
  }

  await page.goto(`/#profile/${author.id}`);
  await expect(page.getByRole('heading', { level: 1, name: 'Profile Author ' + suffix })).toBeVisible();
  await expect(page.locator('.gami-xp-total')).toHaveText('60 XP'); // 50 for the upload + 10 once, repeats ignored
  await expect(page.getByText(`A student downloaded “${title}”`)).toHaveCount(1);
  await expect(page.getByRole('img', { name: '1 active days' })).toBeVisible();
  await expect(page.getByText('Security Champion')).toHaveCount(0); // private badge is never shown to others

  // An uploaded material opens the Materials search for it.
  await page.getByRole('button', { name: title }).click();
  await expect(page).toHaveURL(/#materials$/);
  await expect(page.getByRole('heading', { name: title })).toBeVisible();

  // Others see that the reader studied something, but not what.
  await page.goto(`/#profile/${reader.id}`);
  await expect(page.getByText('Studied a material')).toBeVisible();
  await expect(page.getByText(title)).toHaveCount(0);

  await page.goto('/#profile/999999999');
  await expect(page.getByRole('alert')).toHaveText('This student profile does not exist or is not public.');
});

test('a student reaches their own profile from the header and from the leaderboard', async ({ page, request }) => {
  const me = await student(request, 'Profile Owner ' + stamp());
  await signIn(page, me.email);
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('button', { name: 'Leaderboard' }).click();
  await page.getByRole('link', { name: 'Open my public profile' }).click();
  await expect(page).toHaveURL(new RegExp(`#profile/${me.id}$`));
  await expect(page.getByText('This is you')).toBeVisible();
  await expect(page.getByText('Not ranked yet')).toBeVisible();
  await expect(page.getByText('No materials uploaded yet.')).toBeVisible();

  await page.getByRole('link', { name: '← Back to leaderboard' }).click();
  const firstRanked = page.getByRole('table').getByRole('link').first();
  const name = await firstRanked.textContent();
  await firstRanked.click();
  await expect(page).toHaveURL(/#profile\/\d+$/);
  await expect(page.getByRole('heading', { level: 1, name })).toBeVisible();
  await expect(page.getByText('#1 on the leaderboard')).toBeVisible();
});

import { expect, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const API = 'http://127.0.0.1:8001/api';

function pdfFixture() {
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 72 72] >>',
  ];
  let pdf = '%PDF-1.4\n';
  const offsets = [];
  for (const [index, body] of objects.entries()) {
    offsets.push(pdf.length);
    pdf += `${index + 1} 0 obj\n${body}\nendobj\n`;
  }
  const start = pdf.length;
  pdf += 'xref\n0 4\n0000000000 65535 f \n';
  pdf += offsets.map(offset => String(offset).padStart(10, '0') + ' 00000 n \n').join('');
  return Buffer.from(pdf + `trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n${start}\n%%EOF\n`);
}

test('Week 13 upload decisions through the existing browser form', async ({ page, request }) => {
  test.skip(process.env.MATERIAL_VALIDATOR_V2_ENABLED !== 'true', 'Run the dedicated Week 13 browser command');
  const preview = process.env.MATERIAL_VALIDATOR_V2_MODEL === 'minilm_preview';
  const student = process.env.MATERIAL_VALIDATOR_V2_MODEL === 'v2_2';
  const evidence = new URL(
    student ? '../../ml_moderation/reports/week13/phase3/browser/'
      : '../../ml_moderation/reports/week13/phase2/browser/',
    import.meta.url,
  );
  const email = `week13-${randomUUID()}@example.com`;
  const password = 'Browser-week13-test-13!';
  expect((await request.post(`${API}/auth/register`, {
    data: { full_name: 'Week 13 Browser Fixture', email, password },
  })).status()).toBe(201);
  await page.addInitScript(() => localStorage.setItem('sme-language', 'en'));
  await page.goto('/#login');
  await page.locator('input[name=email]').fill(email);
  await page.locator('input[name=password]').fill(password);
  await page.locator('form button[type=submit], form button.primary').click();
  await expect(page.getByRole('button', { name: 'Log out' })).toBeVisible();
  await page.getByRole('button', { name: 'Upload', exact: true }).click();
  await mkdir(evidence, { recursive: true });
  const courseResponse = await request.get(`${API}/courses`);
  expect(courseResponse.ok()).toBeTruthy();
  const courses = Object.fromEntries((await courseResponse.json()).items
    .map(row => [row.course_code, String(row.course_id)]));
  const cases = student ? [
    ['student-relevant', 'SQL Joins and Queries', 'DB101', 201],
    ['student-uncertain', 'Lecture 5', 'DB101', 201],
    ['student-week12-rejected', 'pppAAASSSS', 'DB101', 422],
  ] : preview ? [
    ['preview-paraphrase-accepted', 'Storing an address only once when several orders share it', 'DB101', 201],
  ] : [
    ['v2-paraphrase-rejected', 'Storing an address only once when several orders share it', 'DB101', 422],
    ['correct-course-generic-file', 'SQL Joins and Queries', 'DB101', 201],
    ['wrong-course', 'SQL Joins and Queries', 'PROG101', 422],
    ['meaningless', 'asdfghjkl', 'DB101', 422],
    ['inappropriate', 'pppAAASSSS', 'DB101', 422],
    ['unfamiliar-paraphrase', 'Constraints for parent-child table relationships', 'DB101', 422],
  ];
  for (const [name, title, course, expected] of cases) {
    await test.step(name, async () => {
      await page.locator('input[name=title]').fill(title);
      await page.locator('select[name=category_id]').selectOption({ label: 'Lecture Notes' });
      expect(courses[course]).toBeDefined();
      await page.locator('select[name=course_id]').selectOption(courses[course]);
      await page.locator('input[type=file]').setInputFiles({
        name: 'document_123.pdf', mimeType: 'application/pdf', buffer: pdfFixture(),
      });
      const response = page.waitForResponse(res =>
        res.request().method() === 'POST' && res.url() === `${API}/materials`,
      );
      await page.locator('form').getByRole('button', { name: 'Upload', exact: true }).click();
      expect((await response).status()).toBe(expected);
      await expect(page.locator(expected === 201 ? 'form [role=status]' : 'form [role=alert]')).toBeVisible();
      await page.screenshot({ path: fileURLToPath(new URL(`${name}.png`, evidence)) });
    });
  }
});

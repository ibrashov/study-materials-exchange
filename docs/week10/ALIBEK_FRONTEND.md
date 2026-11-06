# Alibek — frontend, forms and languages

2026-11-05 · Anuarbek Alibek · 24B031648.

**Implementation prepared by Codex. Personally verified by Alibek: pending.**

## Result and files

The existing React shell, HomePage, shared api/client.js and BackendStatus component are extended. Added features/auth/AuthForm.jsx; features/materials/Materials.jsx and UploadForm.jsx; features/admin/AdminPage.jsx (Arnur review); locales/messages.js. Updated App.jsx, HomePage.jsx and styles.css. No design library or replacement application was introduced.

Registration validates required fields, email shape, 12–128-character password and matching confirmation, then calls the real API. It shows success only after 201, duplicate/network errors, and disables controls while submitting. Login calls auth/login then auth/me. Tokens are in React memory; refresh logs out. Materials queries the backend, displays loading/error/empty states, paginates and downloads real bytes. Upload selectors use backend category/course IDs.

## Design reference

Read directly as references, without installers:

- [design-taste](https://github.com/madebymustafa/design-taste/blob/main/skills/design-taste/SKILL.md): infer the audience first, restrained color, clear hierarchy and avoid decorative defaults.
- [corporate-trust](https://github.com/madebymustafa/design-taste/blob/main/skills/corporate-trust/SKILL.md): light surfaces, readable system typography, borders and almost no motion.

Applied only guidance suitable for the requested early academic prototype: one blue accent, compact forms and small radii. Oversized marketing layouts, corporate claims and legal/compliance decoration were unnecessary and were not added. Desktop Russian and 390px mobile screenshots were inspected; a hover contrast issue was corrected.

## Languages and tests

App holds en/ru state and passes a lightweight t(key) function. messages.js covers navigation, registration/login/upload labels, primary buttons, common errors and material headings. Error state stores translation keys, so existing errors switch language too. document.lang updates. Technical health diagnostics, course/category data and user-entered material titles are not translated; Kazakh is not implemented. Language preference is session-only.

Vite build passed. Seven browser tests passed, including validation, duplicate/API/network errors, EN/RU switching, the full PostgreSQL workflow, admin access and mobile overflow. Two existing API-client tests passed. No fake materials are displayed.

## Personal review and Week 11

Alibek must trace form → central client → response, test both languages and use keyboard-only navigation. By 2026-11-13: translate remaining health/status text and run a documented keyboard/accessibility check on all five feature views at 390px and desktop. Include at least three personally verified improvements and regression screenshots. Full accessibility audit and Kazakh remain future work.

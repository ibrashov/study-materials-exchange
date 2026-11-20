// Shared text helpers for XP events, so the leaderboard card and profiles read the same in every language.
const MATERIAL_ACTIONS = new Set(['upload_material', 'upload_revoked', 'download_material', 'received_download']);

// Events about a material are translated around its title. The title comes from the API, or from the
// stored English description when the material was deleted later; a hidden title means a private download.
export function eventText(event, t) {
  const key = `gamification.event.${event.action}`;
  if (!MATERIAL_ACTIONS.has(event.action)) {
    const text = t(key);
    return text === key ? event.description : text;
  }
  const title = event.material_title ?? event.description?.match(/"(.*)"/)?.[1];
  if (!title) return event.action === 'download_material' ? t('gamification.event.download_private') : event.description;
  return t(key, { title });
}

// "2026-11-20" is a calendar day, not a moment: format it in UTC so no time zone can shift it.
export function formatDay(value, t) {
  const day = new Date(value + 'T00:00:00Z');
  if (Number.isNaN(day.getTime())) return value;
  return day.toLocaleDateString(t('locale'), { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
}

export const formatPoints = points => (points < 0 ? `−${Math.abs(points)}` : `+${points}`);

// Days of the activity heatmap: whole weeks (Monday first) ending with the API's local "today".
export function activityWeeks(days, today, windowDays) {
  const xpByDate = new Map(days.map(day => [day.date, day.xp]));
  const end = new Date(today + 'T00:00:00Z');
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - (windowDays - 1));
  start.setUTCDate(start.getUTCDate() - ((start.getUTCDay() + 6) % 7));
  const weeks = [];
  for (const day = new Date(start); day <= end; day.setUTCDate(day.getUTCDate() + 1)) {
    if ((day.getUTCDay() + 6) % 7 === 0) weeks.push([]);
    const date = day.toISOString().slice(0, 10);
    weeks[weeks.length - 1].push({ date, xp: xpByDate.get(date) ?? 0 });
  }
  return weeks;
}

export const heatLevel = xp => (xp <= 0 ? 0 : xp < 10 ? 1 : xp < 30 ? 2 : xp < 60 ? 3 : 4);

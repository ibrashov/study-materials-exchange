import React from 'react';
import { getStudentProfile } from '../../api/client';
import { errorKey } from '../../locales/messages';
import { formatUploadedAt } from '../materials/format';
import { useRequest } from '../materials/useRequest';
import { activityWeeks, eventText, formatDay, formatPoints, heatLevel } from './format';

const initials = name => name.split(/\s+/).filter(Boolean).slice(0, 2).map(part => part[0].toUpperCase()).join('');

// Public gamification profile of one student: level, badges, XP sources, activity and uploads.
export default function ProfilePage({ userId, session, t, onSearch }) {
  const token = session?.token;
  const profile = useRequest(signal => getStudentProfile(userId, token, signal), [userId, token]);

  return <section className="profile-page">
    <p className="back-link"><a href="#leaderboard">{t('profile.back')}</a></p>
    {profile.status === 'error'
      ? profile.error?.status === 404
        ? <p role="alert" className="gami-card">{t('profile.notFound')}</p>
        : <div role="alert" className="gami-card"><p>{t(errorKey(profile.error))}</p><button onClick={profile.retry}>{t('retry')}</button></div>
      : !profile.data ? <p>{t('loading')}</p> : <ProfileBody p={profile.data} t={t} onSearch={onSearch}/>}
  </section>;
}

function ProfileBody({ p, t, onSearch }) {
  const date = value => formatUploadedAt(value, t);
  const earned = p.badges.filter(badge => badge.earned);
  const sources = p.xp_breakdown.filter(source => source.xp > 0);
  const topSource = Math.max(1, ...sources.map(source => source.xp));
  const weeks = activityWeeks(p.activity_days, p.today, p.activity_window_days);
  const timeline = [
    ...p.recent_events.map(event => ({
      key: 'e' + event.event_id, at: event.created_at, points: event.points, text: eventText(event, t),
    })),
    ...earned.map(badge => ({
      key: 'b' + badge.code, at: badge.earned_at, icon: badge.icon,
      text: t('gamification.event.badge', { title: t(`gamification.badge.${badge.code}`) }),
    })),
  ].sort((a, b) => (new Date(b.at) - new Date(a.at)) || (a.icon ? -1 : b.icon ? 1 : 0)).slice(0, 25);

  return <>
    <div className="gami-card profile-head">
      <span className="avatar" aria-hidden="true">{initials(p.full_name)}</span>
      <div>
        <h1>{p.full_name}</h1>
        <p className="profile-meta">
          {p.is_self && <span className="chip-you">{t('profile.you')}</span>}
          <span>{p.rank ? t('profile.rank', { count: p.rank }) : t('profile.unranked')}</span>
          {p.last_active_on && <span>{t('profile.lastActive', { date: formatDay(p.last_active_on, t) })}</span>}
        </p>
      </div>
    </div>

    <div className="gami-card">
      <div className="gami-hero">
        <div className="gami-level-box">
          <span className="gami-level-badge">{t('gamification.levelLabel', { count: p.level })}</span>
          <strong className="gami-rank-name">{t(`gamification.rank.${p.level_code}`)}</strong>
        </div>
        <div className="gami-xp-meta">
          <span className="gami-xp-total">{t('gamification.xpValue', { count: p.xp_points })}</span>
          <span className="muted">{p.next_level_xp !== null
            ? t('gamification.nextLevel', { count: p.next_level_xp - p.xp_points })
            : t('gamification.maxLevel')}</span>
        </div>
      </div>
      <div className="gami-progress-track" role="progressbar" aria-label={t('gamification.levelLabel', { count: p.level })}
        aria-valuenow={p.progress_percent} aria-valuemin={0} aria-valuemax={100}>
        <div className="gami-progress-fill" style={{ width: `${p.progress_percent}%` }}/>
      </div>
      <dl className="gami-stats">
        <div><dt>{t('gamification.streak')}</dt><dd>{t('gamification.days', { count: p.current_streak })}</dd></div>
        <div><dt>{t('gamification.longestStreak')}</dt><dd>{t('gamification.days', { count: p.longest_streak })}</dd></div>
        <div><dt>{t('gamification.uploads')}</dt><dd>{p.materials_count}</dd></div>
        <div><dt>{t('gamification.downloadsReceived')}</dt><dd>{p.total_downloads_received}</dd></div>
        <div><dt>{t('profile.studentsReached')}</dt><dd>{p.students_reached}</dd></div>
        <div><dt>{t('profile.materialsStudied')}</dt><dd>{p.materials_studied}</dd></div>
      </dl>
    </div>

    <div className="gami-card">
      <h2>{t('profile.activity')}</h2>
      <p className="muted">{t('profile.activitySummary', { count: p.activity_days.length })}</p>
      <div className="heatmap" role="img" aria-label={t('profile.activitySummary', { count: p.activity_days.length })}>
        {weeks.map(week => <div className="heat-week" key={week[0].date}>
          {week.map(day => <span key={day.date} className="heat-cell" data-level={heatLevel(day.xp)}
            title={t('profile.activityDay', { date: formatDay(day.date, t), count: day.xp })}/>)}
        </div>)}
      </div>
      <div className="heat-legend" aria-hidden="true">
        <span>{t('profile.less')}</span>
        {[0, 1, 2, 3, 4].map(level => <span key={level} className="heat-cell" data-level={level}/>)}
        <span>{t('profile.more')}</span>
      </div>
    </div>

    <div className="profile-grid">
      <div className="gami-card">
        <h2>{t('gamification.badges')}</h2>
        <p className="muted">{t('profile.badgesCount', { count: earned.length, total: p.badges.length })}</p>
        <ul className="badge-grid compact">
          {p.badges.map(badge => <li key={badge.code} className={badge.earned ? 'badge-card earned' : 'badge-card locked'}>
            <span className="badge-icon" aria-hidden="true">{badge.icon}</span>
            <div>
              <strong>{t(`gamification.badge.${badge.code}`)}</strong>
              <p>{badge.earned ? t('profile.badgeEarnedOn', { date: date(badge.earned_at) }) : t(`gamification.badgeHint.${badge.code}`)}</p>
            </div>
          </li>)}
        </ul>
      </div>

      <div className="gami-card">
        <h2>{t('profile.xpSources')}</h2>
        {sources.length === 0 ? <p className="muted">{t('profile.noActivity')}</p>
          : <ul className="xp-sources">
            {sources.map(source => <li key={source.source}>
              <span>{t(`profile.source.${source.source}`)}</span>
              <strong>{t('gamification.xpValue', { count: source.xp })}</strong>
              <span className="xp-bar" aria-hidden="true"><span style={{ width: `${(source.xp / topSource) * 100}%` }}/></span>
            </li>)}
          </ul>}
      </div>
    </div>

    <div className="gami-card">
      <h2>{t('profile.uploads')}</h2>
      {p.uploads.length === 0 ? <p className="muted">{t('profile.noUploads')}</p>
        : <ul className="profile-uploads">
          {p.uploads.map(item => <li key={item.material_id}>
            <button className="link" title={t('profile.findMaterial', { title: item.title })}
              onClick={() => onSearch({ q: item.title })}>{item.title}</button>
            <span className="muted">{item.course_code} · {item.category_name}</span>
            <span className="profile-upload-stats">{t('profile.downloads', { count: item.download_count })} · {date(item.uploaded_at)}</span>
          </li>)}
        </ul>}
    </div>

    <div className="gami-card">
      <h2>{t('profile.timeline')}</h2>
      {timeline.length === 0 ? <p className="muted">{t('profile.noActivity')}</p>
        : <ul className="xp-events">
          {timeline.map(item => <li key={item.key}>
            {item.icon
              ? <span className="xp-delta badge-delta" aria-hidden="true">{item.icon}</span>
              : <span className={item.points < 0 ? 'xp-delta negative' : 'xp-delta'}>{formatPoints(item.points)}</span>}
            <span className="xp-desc">{item.text}</span>
            <span className="muted">{date(item.at)}</span>
          </li>)}
        </ul>}
    </div>
  </>;
}

import React from 'react';
import { getLeaderboard, getMyGamification } from '../../api/client';
import { errorKey } from '../../locales/messages';
import { formatUploadedAt } from '../materials/format';
import { useRequest } from '../materials/useRequest';
import { eventText, formatPoints } from './format';

const MEDALS = ['🥇', '🥈', '🥉'];

export default function GamificationPage({ session, t }) {
  const token = session?.token;
  const profile = useRequest(signal => token ? getMyGamification(token, signal) : Promise.resolve(null), [token]);
  const board = useRequest(signal => getLeaderboard(20, signal), []);

  const me = profile.data;

  return <section className="gamification-page">
    <h1>{t('leaderboard')}</h1>
    <p className="intro">{t('gamification.intro')}</p>

    {session && <div className="gami-card">
      <div className="gami-card-head">
        <h2>{t('gamification.myProgress')}</h2>
        {session.user.role === 'student' && <a href={`#profile/${session.user.user_id}`}>{t('gamification.myProfile')}</a>}
      </div>
      {profile.status === 'error' ? <div role="alert"><p>{t(errorKey(profile.error))}</p><button onClick={profile.retry}>{t('retry')}</button></div>
        : !me ? <p>{t('loading')}</p> : <>
          <div className="gami-hero">
            <div className="gami-level-box">
              <span className="gami-level-badge">{t('gamification.levelLabel', { count: me.level })}</span>
              <strong className="gami-rank-name">{t(`gamification.rank.${me.level_code}`)}</strong>
            </div>
            <div className="gami-xp-meta">
              <span className="gami-xp-total">{t('gamification.xpValue', { count: me.xp_points })}</span>
              <span className="muted">
                {me.next_level_xp !== null
                  ? t('gamification.nextLevel', { count: me.next_level_xp - me.xp_points })
                  : t('gamification.maxLevel')}
              </span>
            </div>
          </div>
          <div className="gami-progress-track" role="progressbar" aria-label={t('gamification.levelLabel', { count: me.level })} aria-valuenow={me.progress_percent} aria-valuemin={0} aria-valuemax={100}>
            <div className="gami-progress-fill" style={{ width: `${me.progress_percent}%` }}/>
          </div>
          <dl className="gami-stats">
            <div><dt>{t('gamification.streak')}</dt><dd>{t('gamification.days', { count: me.current_streak })}</dd></div>
            <div><dt>{t('gamification.longestStreak')}</dt><dd>{t('gamification.days', { count: me.longest_streak })}</dd></div>
            <div><dt>{t('gamification.uploads')}</dt><dd>{me.materials_count}</dd></div>
            <div><dt>{t('gamification.downloadsReceived')}</dt><dd>{me.total_downloads_received}</dd></div>
          </dl>

          <h3>{t('gamification.badges')}</h3>
          <ul className="badge-grid">
            {me.badges.map(badge => <li key={badge.code} className={badge.earned ? 'badge-card earned' : 'badge-card locked'}>
              <span className="badge-icon" aria-hidden="true">{badge.icon}</span>
              <div>
                <strong>{t(`gamification.badge.${badge.code}`)}</strong>
                <p>{t(`gamification.badgeHint.${badge.code}`)}</p>
              </div>
            </li>)}
          </ul>

          {me.recent_events.length > 0 && <>
            <h3>{t('gamification.recentActivity')}</h3>
            <ul className="xp-events">
              {me.recent_events.slice(0, 8).map(ev => <li key={ev.event_id}>
                <span className={ev.points < 0 ? 'xp-delta negative' : 'xp-delta'}>{formatPoints(ev.points)}</span>
                <span className="xp-desc">{eventText(ev, t)}</span>
                <span className="muted">{formatUploadedAt(ev.created_at, t)}</span>
              </li>)}
            </ul>
          </>}
        </>}
    </div>}

    <div className="gami-card">
      <h2>{t('gamification.topStudents')}</h2>
      {board.status === 'error' ? <div role="alert"><p>{t(errorKey(board.error))}</p><button onClick={board.retry}>{t('retry')}</button></div>
        : board.data === undefined ? <p>{t('loading')}</p>
          : board.data.items.length === 0 ? <p>{t('admin.nothing')}</p>
            : <div className="admin-table" tabIndex={0}>
              <table>
                <thead>
                  <tr>
                    <th scope="col">#</th>
                    <th scope="col">{t('admin.name')}</th>
                    <th scope="col">{t('gamification.rankCol')}</th>
                    <th scope="col">{t('gamification.xpCol')}</th>
                    <th scope="col">{t('gamification.uploads')}</th>
                    <th scope="col">{t('admin.downloadCount')}</th>
                    <th scope="col">{t('gamification.badges')}</th>
                  </tr>
                </thead>
                <tbody>
                  {board.data.items.map(row => <tr key={row.user_id} className={session?.user.user_id === row.user_id ? 'is-me' : undefined}>
                    <td>{MEDALS[row.rank - 1] || row.rank}</td>
                    <td><a className="profile-link" href={`#profile/${row.user_id}`} title={t('gamification.viewProfile', { title: row.full_name })}>{row.full_name}</a></td>
                    <td>{t(`gamification.rank.${row.level_code}`)}</td>
                    <td><strong>{row.xp_points}</strong></td>
                    <td>{row.materials_count}</td>
                    <td>{row.total_downloads}</td>
                    <td>{row.badges_count}</td>
                  </tr>)}
                </tbody>
              </table>
            </div>}
    </div>
  </section>;
}

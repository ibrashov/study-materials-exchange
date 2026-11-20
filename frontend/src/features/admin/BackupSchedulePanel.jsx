import React, { useEffect, useState } from 'react';
import { getAdminBackups, runAdminBackup, updateBackupSchedule } from '../../api/client';
import { errorKey } from '../../locales/messages';
import { formatUploadedAt } from '../materials/format';
import { useRequest } from '../materials/useRequest';
import AdminPanel from './AdminPanel';

export default function BackupSchedulePanel({ token, t }) {
  const backups = useRequest(signal => getAdminBackups(token, signal), [token]);
  const [enabled, setEnabled] = useState(false);
  const [intervalHours, setIntervalHours] = useState(24);
  const [hourUtc, setHourUtc] = useState(2);
  const [keep, setKeep] = useState(7);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const s = backups.data?.schedule;
    if (!s) return;
    setEnabled(Boolean(s.enabled));
    setIntervalHours(s.interval_hours);
    setHourUtc(s.hour_utc);
    setKeep(s.keep);
  }, [backups.data]);

  async function saveSchedule(event) {
    event.preventDefault();
    setSaving(true); setMessage(''); setError('');
    try {
      await updateBackupSchedule({
        enabled,
        interval_hours: Number(intervalHours),
        hour_utc: Number(hourUtc),
        keep: Number(keep),
      }, token);
      setMessage(t('admin.backupsSaved'));
      backups.retry();
    } catch (err) {
      setError(err.message || t(errorKey(err)));
    } finally {
      setSaving(false);
    }
  }

  async function runNow() {
    setRunning(true); setMessage(''); setError('');
    try {
      const created = await runAdminBackup(token);
      setMessage(t('admin.backupCreated', { title: created.name }));
      backups.retry();
    } catch (err) {
      setError(err.message || t(errorKey(err)));
    } finally {
      setRunning(false);
    }
  }

  return <AdminPanel id="admin-backups" title={t('admin.backups')} request={backups} t={t}>{data => {
    const s = data.schedule;
    return <>
      <p className="admin-help">{t('admin.backupsHelp')}</p>
      <p className={s.enabled ? 'status-pill on' : 'status-pill'}>
        {s.enabled ? t('admin.backupsEnabled') : t('admin.backupsPaused')}
      </p>
      {!s.supported && <p className="admin-flag">{t('admin.backupsCloudNote')}</p>}
      <dl className="stats">
        <div><dt>{t('admin.backupsLastRun')}</dt><dd>{s.last_run_at ? formatUploadedAt(s.last_run_at, t) : t('admin.backupsNever')}</dd></div>
        <div><dt>{t('admin.backupsNextRun')}</dt><dd>{s.next_run_at ? formatUploadedAt(s.next_run_at, t) : t('admin.backupsNever')}</dd></div>
        <div><dt>{t('admin.status')}</dt><dd>{s.last_status}</dd></div>
      </dl>
      {s.last_error && <p className="error-text" role="alert">{s.last_error}</p>}

      <form className="admin-config-form" onSubmit={saveSchedule}>
        <label className="check">
          <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)}/>
          {t('admin.backupsToggle')}
        </label>
        <div className="admin-grid-3">
          <label>{t('admin.backupsInterval')}
            <input type="number" min={1} max={720} value={intervalHours} onChange={e => setIntervalHours(e.target.value)} required/>
          </label>
          <label>{t('admin.backupsHourUtc')}
            <input type="number" min={0} max={23} value={hourUtc} onChange={e => setHourUtc(e.target.value)} required/>
          </label>
          <label>{t('admin.backupsKeep')}
            <input type="number" min={1} max={365} value={keep} onChange={e => setKeep(e.target.value)} required/>
          </label>
        </div>
        <div className="row">
          <button type="submit" className="primary" disabled={saving || running}>{saving ? t('saving') : t('admin.backupsSave')}</button>
          <button type="button" disabled={saving || running || !s.supported} onClick={runNow}>{running ? t('saving') : t('admin.backupsRunNow')}</button>
        </div>
      </form>

      {message && <p className="success-text" role="status">{message}</p>}
      {error && <p className="error-text" role="alert">{error}</p>}

      {data.items.length === 0 ? <p>{t('admin.nothing')}</p> : <div className="admin-table" tabIndex={0}>
        <table aria-labelledby="admin-backups">
          <thead>
            <tr>
              <th scope="col">{t('admin.backupName')}</th>
              <th scope="col">{t('admin.materialCount')}</th>
              <th scope="col">{t('admin.backupFiles')}</th>
              <th scope="col">{t('admin.status')}</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map(item => <tr key={item.name}>
              <td><code>{item.name}</code></td>
              <td>{item.tables?.materials ?? 0}</td>
              <td>{item.files}</td>
              <td><span className={item.verified ? 'success-text' : 'admin-flag'}>{item.verified ? t('admin.backupVerified') : t('admin.storageBad')}</span></td>
            </tr>)}
          </tbody>
        </table>
      </div>}
    </>;
  }}</AdminPanel>;
}

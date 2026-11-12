import React, { useState } from 'react';
import { getMe, twoFactorSetup, twoFactorEnable, twoFactorDisable } from '../../api/client';
import { errorKey } from '../../locales/messages';
// Week 11: two-factor authentication (TOTP) management. Secrets live only in component state.
export default function SecurityPage({ session, t, onChange }) {
  const [setup, setSetup] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  if (!session) return <p role="alert">{t('loginRequired')}</p>;
  const enabled = session.user.totp_enabled;
  async function run(action, done) {
    setBusy(true); setError(''); setNotice('');
    try { await action(); const user = await getMe(session.token); onChange(user); setNotice(done); }
    catch (err) { setError(errorKey(err)); }
    finally { setBusy(false); }
  }
  const start = async () => { setBusy(true); setError(''); setNotice(''); try { setSetup(await twoFactorSetup(session.token)); } catch (err) { setError(errorKey(err)); } finally { setBusy(false); } };
  const enable = event => { event.preventDefault(); const code = new FormData(event.currentTarget).get('code').trim(); run(async () => { await twoFactorEnable(code, session.token); setSetup(null); }, 'twoFactorEnabledMsg'); };
  const disable = event => { event.preventDefault(); const d = new FormData(event.currentTarget); const body = { password: d.get('password'), code: d.get('code').trim() }; run(() => twoFactorDisable(body, session.token), 'twoFactorDisabledMsg'); };
  const copy = async () => { try { await navigator.clipboard.writeText(setup.secret); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch { /* clipboard unavailable */ } };
  return <section className="form-panel"><h1>{t('twoFactor')}</h1>
    <p className={enabled ? 'status-pill on' : 'status-pill'} role="status">{t(enabled ? 'twoFactorOn' : 'twoFactorOff')}</p>
    {error && <p role="alert" className="error-text">{t(error)}</p>}
    {notice && <p role="status" className="success-text">{t(notice)}</p>}
    {!enabled && !setup && <button className="primary" onClick={start} disabled={busy}>{t('enableTwoFactor')}</button>}
    {!enabled && setup && <form onSubmit={enable}>
      <p>{t('setupSteps')}</p>
      <label>{t('secretKey')}<input readOnly value={setup.secret} onFocus={e => e.target.select()} className="mono"/></label>
      <div className="row"><button type="button" onClick={copy}>{t(copied ? 'copied' : 'copy')}</button></div>
      <label>{t('otpCode')}<input name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]*" maxLength={6} required disabled={busy}/></label>
      <div className="row"><button className="primary" disabled={busy}>{t('confirmEnable')}</button><button type="button" onClick={() => setSetup(null)}>{t('cancel')}</button></div>
    </form>}
    {enabled && <form onSubmit={disable}>
      <label>{t('password')}<input name="password" type="password" autoComplete="current-password" required disabled={busy}/></label>
      <label>{t('otpCode')}<input name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]*" maxLength={6} required disabled={busy}/></label>
      <button disabled={busy}>{t('disableTwoFactor')}</button>
    </form>}
  </section>;
}

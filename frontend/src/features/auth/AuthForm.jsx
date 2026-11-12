import React, { useState } from 'react';
import { register, login, getMe } from '../../api/client';
import { errorKey } from '../../locales/messages';
export default function AuthForm({ mode, t, onLogin }) {
  const isRegister = mode === 'registration';
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [needOtp, setNeedOtp] = useState(false);
  const [reveal, setReveal] = useState(false);
  async function submit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    setError(''); setSuccess(false);
    if (!values.email.trim() || !values.password || (isRegister && (!values.full_name.trim() || !values.confirm))) return setError('required');
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) return setError('invalidEmail');
    if (isRegister && (values.password.length < 12 || values.password.length > 128)) return setError('passwordLength');
    if (isRegister && values.password !== values.confirm) return setError('mismatch');
    setBusy(true);
    try {
      if (isRegister) {
        await register({ full_name: values.full_name.trim(), email: values.email.trim(), password: values.password });
        setSuccess(true); form.reset();
      } else {
        const body = { email: values.email.trim(), password: values.password };
        if (needOtp && values.otp?.trim()) body.otp = values.otp.trim();
        const data = await login(body);
        const user = await getMe(data.access_token);
        onLogin({ user, token: data.access_token });
      }
    } catch (err) {
      if (!isRegister && err.status === 401 && err.message === 'otp_required') setNeedOtp(true);
      setError(errorKey(err, mode));
    }
    finally { setBusy(false); }
  }
  const type = reveal ? 'text' : 'password';
  return <section className="form-panel"><h1>{t(mode)}</h1>
    <form onSubmit={submit} noValidate>
      {isRegister && <label>{t('fullName')}<input name="full_name" autoComplete="name" maxLength={120} required disabled={busy}/></label>}
      <label>{t('email')}<input name="email" type="email" autoComplete="email" maxLength={254} required disabled={busy}/></label>
      <label>{t('password')}<input name="password" type={type} autoComplete={isRegister ? 'new-password' : 'current-password'} maxLength={128} required disabled={busy}/></label>
      <label className="check"><input type="checkbox" checked={reveal} onChange={e => setReveal(e.target.checked)}/>{t('showPassword')}</label>
      {isRegister && <><small>{t('passwordHint')}</small><label>{t('confirm')}<input name="confirm" type={type} autoComplete="new-password" maxLength={128} required disabled={busy}/></label></>}
      {needOtp && <label>{t('otpCode')}<input name="otp" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]*" maxLength={6} autoFocus disabled={busy}/><small>{t('otpHint')}</small></label>}
      {error && <p role="alert" className="error-text">{t(error)}</p>}
      {success && <p role="status" className="success-text">{t('registered')}</p>}
      <button className="primary" disabled={busy}>{t(busy ? 'saving' : isRegister ? 'register' : 'signIn')}</button>
    </form></section>;
}

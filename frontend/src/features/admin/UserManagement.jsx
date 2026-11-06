import React, { useState } from 'react';
import { getUsers, updateUser } from '../../api/client';
import { errorKey } from '../../locales/messages';
import { useRequest } from '../materials/useRequest';
import AdminPanel from './AdminPanel';

const PAGE_SIZE = 50;

export default function UserManagement({ token, currentUserId, t }) {
  const [draft, setDraft] = useState('');
  const [search, setSearch] = useState({ q: '', offset: 0 });
  const [error, setError] = useState('');
  const [working, setWorking] = useState(null);
  const users = useRequest(signal => getUsers({ ...search, limit: PAGE_SIZE, token, signal }), [search, token]);
  async function change(user, body) {
    setWorking(user.user_id); setError('');
    try { await updateUser(user.user_id, body, token); users.retry(); }
    catch (err) { setError(errorKey(err, 'user')); }
    finally { setWorking(null); }
  }
  return <AdminPanel id="admin-users" title={t('admin.users')} request={users} t={t}>{data => <>
    <form className="admin-inline-form" role="search" onSubmit={event => { event.preventDefault(); setSearch({ q: draft, offset: 0 }); }}>
      <label>{t('admin.findUsers')}<input type="search" value={draft} onChange={event => setDraft(event.target.value)}/></label>
      <button type="submit">{t('admin.find')}</button>
    </form>
    {error && <p role="alert">{t(error)}</p>}
    {data.items.length === 0 ? <p>{t('admin.nothing')}</p> : <div className="admin-table"><table aria-labelledby="admin-users">
      <thead><tr><th scope="col">{t('admin.name')}</th><th scope="col">{t('email')}</th><th scope="col">{t('admin.role')}</th><th scope="col">{t('admin.status')}</th><th scope="col"><span className="visually-hidden">{t('admin.block')}</span></th></tr></thead>
      <tbody>{data.items.map(user => { const self = user.user_id === currentUserId; return <tr key={user.user_id}>
        <td>{user.full_name}</td><td>{user.email}</td>
        <td><select aria-label={t('admin.role') + ': ' + user.email} value={user.role} disabled={self || working !== null} onChange={event => change(user, { role: event.target.value })}>
          <option value="student">{t('admin.roleStudent')}</option><option value="admin">{t('admin.roleAdmin')}</option></select></td>
        <td>{t(user.is_active ? 'admin.active' : 'admin.blocked')}</td>
        <td><button disabled={self || working !== null} onClick={() => change(user, { is_active: !user.is_active })}>{t(user.is_active ? 'admin.block' : 'admin.unblock')}</button></td>
      </tr>; })}</tbody></table></div>}
    {data.total > data.limit && <nav className="materials-pager" aria-label={t('admin.users')}>
      <button disabled={data.offset === 0} onClick={() => setSearch(current => ({ ...current, offset: Math.max(0, data.offset - data.limit) }))}>{t('previous')}</button>
      <button disabled={data.offset + data.items.length >= data.total} onClick={() => setSearch(current => ({ ...current, offset: data.offset + data.limit }))}>{t('next')}</button>
    </nav>}
  </>}</AdminPanel>;
}

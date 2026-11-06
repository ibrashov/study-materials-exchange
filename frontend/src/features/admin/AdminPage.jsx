import React from 'react';
import { getCourseReport, getDownloadReport, getOverview, getStorageCheck } from '../../api/client';
import { useRequest } from '../materials/useRequest';
import AdminPanel from './AdminPanel';
import TaxonomyForms from './TaxonomyForms';
import UserManagement from './UserManagement';
import './admin.css';

function Dashboard({ session, t }) {
  const { token } = session;
  const overview = useRequest(signal => getOverview(token, signal), [token]);
  const courses = useRequest(signal => getCourseReport(token, signal), [token]);
  const downloads = useRequest(signal => getDownloadReport(token, signal), [token]);
  const storage = useRequest(signal => getStorageCheck(token, signal), [token]);
  return <section><h1>{t('admin')}</h1>
    <AdminPanel id="admin-overview" title={t('admin')} request={overview} t={t}>{data => <dl className="stats">
      <div><dt>{t('totalUsers')}</dt><dd>{data.total_users}</dd></div>
      <div><dt>{t('totalMaterials')}</dt><dd>{data.total_materials}</dd></div>
    </dl>}</AdminPanel>
    <AdminPanel id="admin-courses" title={t('admin.courses')} request={courses} t={t}>{data => <>
      <p className="admin-help">{t('admin.coursesHelp')}</p>
      {data.items.length === 0 ? <p>{t('admin.nothing')}</p> : <div className="admin-table"><table aria-labelledby="admin-courses">
        <thead><tr><th scope="col">{t('course')}</th><th scope="col">{t('admin.code')}</th><th scope="col">{t('admin.materialCount')}</th></tr></thead>
        <tbody>{data.items.map(row => <tr key={row.course_id}><td>{row.course_name}</td><td>{row.course_code}</td>
          <td>{row.material_count === 0 ? <span className="admin-flag">{t('admin.noMaterials')}</span> : row.material_count}</td></tr>)}</tbody>
      </table></div>}</>}</AdminPanel>
    <AdminPanel id="admin-downloads" title={t('admin.downloads')} request={downloads} t={t}>{data => <>
      <dl className="stats"><div><dt>{t('admin.totalDownloads')}</dt><dd>{data.total_downloads}</dd></div></dl>
      {data.items.length === 0 ? <p>{t('admin.nothing')}</p> : <div className="admin-table"><table aria-labelledby="admin-downloads">
        <thead><tr><th scope="col">{t('admin.material')}</th><th scope="col">{t('course')}</th><th scope="col">{t('admin.downloadCount')}</th></tr></thead>
        <tbody>{data.items.map(row => <tr key={row.material_id}><td>{row.title}</td><td>{row.course_name}</td><td>{row.download_count}</td></tr>)}</tbody>
      </table></div>}</>}</AdminPanel>
    <UserManagement token={token} currentUserId={session.user.user_id} t={t}/>
    <TaxonomyForms token={token} onAdded={courses.retry} t={t}/>
    <AdminPanel id="admin-storage" title={t('admin.storage')} request={storage} t={t}>{data => {
      const clean = data.orphan_files + data.partial_files + data.missing_files === 0;
      return <><p className={clean ? 'success-text' : 'admin-flag'}>{t(clean ? 'admin.storageOk' : 'admin.storageBad')}</p>
        <dl className="stats"><div><dt>{t('admin.orphans')}</dt><dd>{data.orphan_files}</dd></div>
          <div><dt>{t('admin.partial')}</dt><dd>{data.partial_files}</dd></div>
          <div><dt>{t('admin.missing')}</dt><dd>{data.missing_files}</dd></div></dl>
        {!clean && <p className="admin-help">{t('admin.storageHelp')}</p>}</>;
    }}</AdminPanel>
  </section>;
}

export default function AdminPage({ session, t }) {
  // The server enforces this on every route; the check only avoids pointless failed requests.
  if (session?.user.role !== 'admin') return <section><h1>{t('admin')}</h1><p role="alert">{t('denied')}</p></section>;
  return <Dashboard session={session} t={t}/>;
}

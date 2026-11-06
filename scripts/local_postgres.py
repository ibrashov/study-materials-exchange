"""Isolated local PostgreSQL; never modifies an existing service."""
import argparse
import os
from pathlib import Path
import secrets
import shutil
import subprocess
ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / '.local-postgres'
DATA = LOCAL / 'data'
PORT = '55432'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'stop'], nargs='?', default='start')
    args = parser.parse_args()
    pg_bin = Path(os.environ.get('PG_BIN', 'C:/Program Files/PostgreSQL/17/bin'))
    def run(name, *args, check=True, **kwargs):
        executable = shutil.which(name) or str(pg_bin / (name + '.exe'))
        return subprocess.run([executable, *map(str, args)], check=check, **kwargs)
    if args.action == 'stop':
        run('pg_ctl', '-D', DATA, '-m', 'fast', '-w', 'stop')
        return
    LOCAL.mkdir(exist_ok=True)
    password_file = LOCAL / 'password'
    if not DATA.exists():
        password_file.write_text(secrets.token_hex(24), encoding='ascii')
        run('initdb', '-D', DATA, '-U', 'sme_local', '--auth=scram-sha-256',
            '--encoding=UTF8', '--locale=C', '--pwfile', password_file)
    password = password_file.read_text(encoding='ascii').strip()
    status = run('pg_ctl', '-D', DATA, 'status', check=False, capture_output=True)
    if status.returncode != 0:
        run('pg_ctl', '-D', DATA, '-l', LOCAL / 'server.log', '-o', f'-h 127.0.0.1 -p {PORT}', '-w', 'start')
    import psycopg
    with psycopg.connect(host='127.0.0.1', port=PORT, user='sme_local', password=password,
                         dbname='postgres', autocommit=True) as conn:
        for database in ('study_materials', 'study_materials_test'):
            if conn.execute('SELECT 1 FROM pg_database WHERE datname=%s', (database,)).fetchone() is None:
                conn.execute(psycopg.sql.SQL('CREATE DATABASE {}').format(psycopg.sql.Identifier(database)))
    env_path = ROOT / 'backend' / '.env'
    if not env_path.exists():
        prefix = f'postgresql+psycopg://sme_local:{password}@127.0.0.1:{PORT}/'
        lines = [f'DATABASE_URL={prefix}study_materials', f'TEST_DATABASE_URL={prefix}study_materials_test', f'AUTH_SECRET={secrets.token_hex(32)}', '']
        env_path.write_text(chr(10).join(lines), encoding='utf-8')
        print('Created ignored backend/.env with generated local credentials.')
    else:
        print('Preserved existing backend/.env. Configure it for this instance if needed.')
    print(f'Project PostgreSQL ready on 127.0.0.1:{PORT}; development and separate test databases exist.')
if __name__ == '__main__':
    main()

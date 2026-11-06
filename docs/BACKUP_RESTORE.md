# Backup and restore

The team chose automatic backup as its first security priority (Task 9). `scripts/backup.py` covers both the PostgreSQL database and the uploaded files, because either one alone cannot restore the library.

Commands below use the macOS/Linux path. On Windows use `.\.venv\Scripts\python.exe` instead of `.venv/bin/python`.

| Goal | Command |
| --- | --- |
| Make a backup and remove old ones | `.venv/bin/python scripts/backup.py create` |
| List backups | `.venv/bin/python scripts/backup.py list` |
| Check the newest backup against its checksums | `.venv/bin/python scripts/backup.py verify` |
| Prove a backup works | `.venv/bin/python scripts/backup.py drill` |
| Restore into the separate `study_materials_restore` database | `.venv/bin/python scripts/backup.py restore` |
| Replace the real data after a disaster | `.venv/bin/python scripts/backup.py restore --live --yes-replace-live-data` |

## How it works

- Each backup is a folder containing `database.dump`, `uploads.tar.gz` and `manifest.json`. The manifest records row counts, the migration revision and SHA-256 checksums. It holds no credentials.
- The dump and the row counts come from one database snapshot, so they agree even while people use the site.
- An unfinished backup is deleted, never left looking complete. Only the newest `BACKUP_KEEP` backups stay (default 7).
- `drill` makes a fresh backup, restores it into a throwaway `*_restore` database, compares row counts and file sizes, then drops that database.
- A restore checks the checksums first and runs in one database transaction, so a failed restore leaves the target unchanged.
- Without `--live`, a restore refuses any database not named `*_restore`.

## What to protect

Backups contain password hashes and every uploaded file. They are created readable only by their owner. Set `BACKUPS_DIR` to a different disk or machine: a backup beside the application server is lost with that server, and ransomware that reaches the server can reach it too.

## Running it automatically

The project does not install a schedule by itself, because the schedule belongs to the machine that hosts the system.

macOS or Linux, using `crontab -e`:

~~~text
0 2 * * * cd /path/to/project && .venv/bin/python scripts/backup.py create >> backups/backup.log 2>&1
0 3 * * 0 cd /path/to/project && .venv/bin/python scripts/backup.py drill >> backups/drill.log 2>&1
~~~

Windows PowerShell:

~~~powershell
schtasks /Create /SC DAILY /ST 02:00 /TN "SME backup" /TR "C:\path\to\project\.venv\Scripts\python.exe C:\path\to\project\scripts\backup.py create"
~~~

## Files and rows out of step

A crash between saving a file and saving its record can leave them out of step. The admin panel shows the counts. For details:

~~~bash
.venv/bin/python scripts/reconcile_storage.py
.venv/bin/python scripts/reconcile_storage.py --remove-older-than-hours 24
~~~

The first command changes nothing. The second removes only unreferenced files older than the limit, so uploads in progress are safe. Files with a record are never removed.

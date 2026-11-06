"""Create, verify, list and restore backups of the database and uploaded files."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.core.config import settings
from backend.app.services import backup

def pick(destination, name):
    found = backup.list_backups(destination)
    if name == 'latest':
        if not found:
            raise backup.BackupError('No backups found')
        return found[-1]
    path = Path(name) if Path(name).is_dir() else Path(destination) / name
    if not path.is_dir():
        raise backup.BackupError(f'Backup not found: {name}')
    return path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, default=settings.backups_dir)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('create', help='make a new backup and remove old ones')
    create.add_argument('--keep', type=int, default=settings.backup_keep)
    commands.add_parser('list', help='show existing backups')
    verify = commands.add_parser('verify', help='check a backup against its checksums')
    verify.add_argument('name', nargs='?', default='latest')
    drill = commands.add_parser('drill', help='back up, restore into a throwaway database and compare')
    drill.add_argument('--keep', type=int, default=settings.backup_keep)
    restore = commands.add_parser('restore', help='restore into the *_restore database, or the live one with --live')
    restore.add_argument('name', nargs='?', default='latest')
    restore.add_argument('--live', action='store_true', help='replace the real database and restore files to UPLOADS_DIR')
    restore.add_argument('--yes-replace-live-data', action='store_true', help='required together with --live')
    restore.add_argument('--files-to', type=Path, default=settings.backups_dir / 'restored-files')
    args = parser.parse_args()
    if not settings.database_url:
        parser.error('Set DATABASE_URL first')
    url = settings.database_url
    try:
        if args.command == 'create':
            path = backup.create_backup(url, settings.uploads_dir, args.destination, keep=args.keep)
            print(json.dumps({'created': path.name, 'tables': backup.verify_backup(path)['tables']}))
        elif args.command == 'list':
            for path in backup.list_backups(args.destination):
                print(path.name)
        elif args.command == 'verify':
            path = pick(args.destination, args.name)
            print(json.dumps({'backup': path.name, 'valid': True, 'tables': backup.verify_backup(path)['tables']}))
        elif args.command == 'drill':
            print(json.dumps(backup.run_drill(url, settings.uploads_dir, args.destination, keep=args.keep)))
        elif args.live:
            if not args.yes_replace_live_data:
                parser.error('--live replaces all current data; add --yes-replace-live-data to confirm')
            print(json.dumps(backup.restore_backup(pick(args.destination, args.name), url, settings.uploads_dir, allow_live=True)))
        else:
            target = backup.restore_url_for(url)
            backup.prepare_restore_database(target)
            print(json.dumps(backup.restore_backup(pick(args.destination, args.name), target, args.files_to)))
    except backup.BackupError as error:
        sys.exit(f'Backup error: {error}')

if __name__ == '__main__':
    main()

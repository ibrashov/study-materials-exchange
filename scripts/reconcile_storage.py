"""Reports files and rows that are out of step. Changes nothing unless asked to remove leftovers."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy.orm import Session
from backend.app.core.config import settings
from backend.app.db.session import engine_for
from backend.app.services.reconcile import remove_leftovers, scan

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remove-older-than-hours', type=float, help='delete unreferenced files at least this old')
    args = parser.parse_args()
    if not settings.database_url:
        parser.error('Set DATABASE_URL first')
    with Session(engine_for(settings.database_url)) as db:
        if args.remove_older_than_hours is not None:
            print(json.dumps({'removed': remove_leftovers(db, args.remove_older_than_hours * 3600)}))
        print(json.dumps(scan(db), indent=2))

if __name__ == '__main__':
    main()

"""Locates PostgreSQL client programs on Windows, macOS and Linux."""
import os
from pathlib import Path
import shutil

SEARCH_DIRS = ('C:/Program Files/PostgreSQL/17/bin', '/opt/homebrew/opt/postgresql@17/bin',
               '/usr/local/opt/postgresql@17/bin', '/usr/lib/postgresql/17/bin')

def pg_tool(name):
    configured = os.environ.get('PG_BIN')
    for directory in ([configured] if configured else []) + list(SEARCH_DIRS):
        for candidate in (Path(directory) / name, Path(directory) / (name + '.exe')):
            if candidate.is_file():
                return str(candidate)
    found = shutil.which(name)
    if found:
        return found
    raise FileNotFoundError(f'{name} not found; set PG_BIN to the PostgreSQL bin directory')

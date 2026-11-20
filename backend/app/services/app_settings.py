"""Persistent JSON key-value settings stored in the app_settings table."""
from datetime import datetime, timezone
import json
from sqlalchemy.orm import Session
from ..models.entities import AppSetting


def get_json_setting(db: Session, key: str, default: dict) -> dict:
    row = db.get(AppSetting, key)
    if row is None:
        return dict(default)
    try:
        loaded = json.loads(row.value_json)
        if isinstance(loaded, dict):
            return {**default, **loaded}
    except (ValueError, TypeError):
        pass
    return dict(default)


def set_json_setting(db: Session, key: str, value: dict) -> dict:
    encoded = json.dumps(value, ensure_ascii=False)
    row = db.get(AppSetting, key)
    now = datetime.now(timezone.utc)
    if row is None:
        db.add(AppSetting(key=key, value_json=encoded, updated_at=now))
    else:
        row.value_json = encoded
        row.updated_at = now
    db.commit()
    return dict(value)

"""SQLite cache for localization briefs. Table: brief_cache(cache_key, brief_json, created_at, expires_at)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS brief_cache (
    cache_key  TEXT PRIMARY KEY,
    brief_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
)
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def make_key(country: str, language: str, dialect_applied: Optional[str], age_group: str) -> str:
    """(country, language, dialect_applied, age_group) -> one string key. Dialect is part of the key."""
    return "|".join([country.upper(), language, dialect_applied or "none", age_group])


class BriefCache:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.execute(SCHEMA)
        self.db.commit()

    def get(self, key: str, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Return the cached brief dict, or None if missing or expired."""
        now = now or utcnow()
        row = self.db.execute(
            "SELECT brief_json, expires_at FROM brief_cache WHERE cache_key = ?", (key,)).fetchone()
        if row is None or datetime.fromisoformat(row[1]) <= now:
            return None
        return json.loads(row[0])

    def put(self, key: str, brief: Dict[str, Any], ttl_days: int, now: Optional[datetime] = None) -> None:
        """Insert or replace the row; expires_at = now + ttl_days."""
        now = now or utcnow()
        self.db.execute(
            "INSERT OR REPLACE INTO brief_cache VALUES (?, ?, ?, ?)",
            (key, json.dumps(brief, ensure_ascii=False), now.isoformat(),
             (now + timedelta(days=ttl_days)).isoformat()))
        self.db.commit()

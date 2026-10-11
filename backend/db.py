"""قاعدة بيانات SQLite (مكتبة بايثون الأساسية، من غير تسطيب حاجة).

دلوقتي الصوت اللي بيرجّعه Cartesia بيتخزّن هنا بدل مجلد tts-cache:
    tts_audio(key PK, text, language, voice, model, audio BLOB, bytes, hits, created_at, last_used_at)

الـ key هو نفس الـ SHA-1 القديم (إعدادات الصوت + النص)، فالملفات القديمة اللي في tts-cache/
بتتنقل لقاعدة البيانات مرة واحدة أوتوماتيك أول ما السيرفر يشتغل ومفيش حاجة بتتحاسب تاني.

مكان الملف: data/lesson_lab.db (ممكن تغيّره بالمتغير DB_PATH في .env).
"""
from __future__ import annotations

import os
import sqlite3
import time
from contextlib import closing, contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY_CACHE = ROOT / "tts-cache"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tts_audio (
    key           TEXT PRIMARY KEY,
    text          TEXT,
    language      TEXT,
    voice         TEXT,
    model         TEXT,
    audio         BLOB NOT NULL,
    bytes         INTEGER NOT NULL,
    hits          INTEGER NOT NULL DEFAULT 0,
    created_at    REAL NOT NULL,
    last_used_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tts_last_used ON tts_audio(last_used_at);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def db_path() -> Path:
    p = Path(os.getenv("DB_PATH") or ROOT / "data" / "lesson_lab.db")
    return p if p.is_absolute() else ROOT / p


_ready: set[str] = set()


@contextmanager
def connect():
    """اتصال جديد لكل عملية (SQLite خفيفة، وده بيخلّينا آمنين مع الـ threads). الجداول بتتعمل أوتوماتيك أول مرة."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=15)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        if str(path) not in _ready:
            conn.executescript(SCHEMA)
            _ready.add(str(path))
        with conn:  # commit / rollback أوتوماتيك
            yield conn


def init() -> None:
    with connect():
        pass


# ----------------------------------------------------------------------------- الصوت

def get_audio(key: str) -> bytes | None:
    with connect() as c:
        row = c.execute("SELECT audio FROM tts_audio WHERE key = ?", (key,)).fetchone()
        if not row:
            return None
        c.execute("UPDATE tts_audio SET hits = hits + 1, last_used_at = ? WHERE key = ?", (time.time(), key))
        return bytes(row[0])


def put_audio(key: str, audio: bytes, *, text: str | None = None, language: str | None = None,
              voice: str | None = None, model: str | None = None) -> None:
    now = time.time()
    with connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO tts_audio (key, text, language, voice, model, audio, bytes, hits, created_at, last_used_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (key, text, language, voice, model, sqlite3.Binary(audio), len(audio), now, now),
        )


def audio_stats() -> dict:
    with connect() as c:
        n, size, hits = c.execute("SELECT COUNT(*), COALESCE(SUM(bytes), 0), COALESCE(SUM(hits), 0) FROM tts_audio").fetchone()
    return {"entries": n, "bytes": size, "hits": hits}


def import_legacy_tts_cache(folder: Path = LEGACY_CACHE) -> int:
    """بينقل ملفات tts-cache/*.mp3 القديمة لقاعدة البيانات مرة واحدة (من غير ما يمسح الملفات). بيرجّع عدد اللي اتنقل."""
    with connect() as c:
        if c.execute("SELECT 1 FROM meta WHERE key = 'legacy_tts_imported'").fetchone():
            return 0
        moved = 0
        if folder.is_dir():
            now = time.time()
            for f in sorted(folder.glob("*.mp3")):
                data = f.read_bytes()
                if not data:
                    continue
                ts = f.stat().st_mtime
                cur = c.execute(
                    "INSERT OR IGNORE INTO tts_audio (key, audio, bytes, hits, created_at, last_used_at) VALUES (?, ?, ?, 0, ?, ?)",
                    (f.stem, sqlite3.Binary(data), len(data), ts, now),
                )
                moved += cur.rowcount
        c.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('legacy_tts_imported', ?)", (str(moved),))
        return moved

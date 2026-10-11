"""قراءة .env وإعادة قراءته أوتوماتيك لما يتغيّر (من غير ريستارت) وبأولوية للملف على متغيرات النظام.

قبل كده load_dotenv كان بيقرأ الملف مرة واحدة وقت التشغيل ومابيغيّرش أي متغير موجود فعلًا في النظام،
فتغيير CARTESIA_VOICE_ID في .env مكانش بيأثر لحد ما تقفل السيرفر وتشغّله، وساعات ولا بعدها.
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
_mtime: float | None = None


def refresh(force: bool = False) -> None:
    global _mtime
    try:
        m = ENV_FILE.stat().st_mtime
    except OSError:
        return
    if force or m != _mtime:
        load_dotenv(ENV_FILE, override=True)
        _mtime = m

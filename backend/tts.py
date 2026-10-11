"""صوت Cartesia. النتيجة بتتخزّن في قاعدة بيانات SQLite (جدول tts_audio) عشان نفس الجملة متتحاسبش مرتين."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os

import httpx

from . import db, envfile
from .arabic import strip_tashkeel


class TTSError(Exception):
    def __init__(self, status: int, msg: str):
        super().__init__(msg)
        self.status = status


def voice_id() -> str:
    envfile.refresh()
    return os.getenv("CARTESIA_VOICE_ID", "")


def enabled() -> bool:
    envfile.refresh()
    return bool(os.getenv("CARTESIA_API_KEY") and os.getenv("CARTESIA_VOICE_ID"))


async def synthesize(text: str, language: str | None = None) -> bytes:
    envfile.refresh()  # أي تغيير في .env (زي CARTESIA_VOICE_ID) بيتطبّق فورًا من غير ريستارت
    text = strip_tashkeel(text).strip()  # فصحى من غير تشكيل ولا تنوين: ده اللي بيتبعت لموديل الصوت
    if not enabled():
        raise TTSError(501, "Cartesia مش متفعّل (CARTESIA_API_KEY / CARTESIA_VOICE_ID)")
    cfg = {
        "model_id": os.getenv("CARTESIA_MODEL", "sonic-3"),
        "language": language or os.getenv("CARTESIA_LANGUAGE", "ar"),
        "voice": os.environ["CARTESIA_VOICE_ID"],
    }
    key = hashlib.sha1(json.dumps([cfg, text], ensure_ascii=False).encode()).hexdigest()
    cached = await asyncio.to_thread(db.get_audio, key)
    if cached is not None:
        return cached
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(
            "https://api.cartesia.ai/tts/bytes",
            headers={
                "Authorization": f"Bearer {os.environ['CARTESIA_API_KEY']}",
                "Cartesia-Version": os.getenv("CARTESIA_VERSION", "2026-03-01"),
            },
            json={
                "model_id": cfg["model_id"],
                "transcript": text,
                "voice": {"id": cfg["voice"]},
                "language": cfg["language"],
                "output_format": {"container": "mp3", "sample_rate": 44100, "bit_rate": 128000},
            },
        )
    if r.status_code >= 400:
        raise TTSError(502, f"Cartesia {r.status_code}: {r.text[:200]}")
    await asyncio.to_thread(
        db.put_audio, key, r.content, text=text, language=cfg["language"], voice=cfg["voice"], model=cfg["model_id"]
    )
    return r.content

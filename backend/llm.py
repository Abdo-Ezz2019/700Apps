"""طبقة الموديل الموحّدة: Gemini هو الأساسي، ولو وقع (زحمة 503 / quota / تايم أوت / أي خطأ)
بيتحوّل كامل على OpenRouter، وبيفضل عليه فترة (LLM_FALLBACK_COOLDOWN) عشان مانستناش Gemini في كل طلب.

المتغيرات في .env:
    LLM_PROVIDER            auto (الافتراضي: Gemini ثم OpenRouter) | gemini (Gemini بس) | openrouter (OpenRouter بس)
    GEMINI_API_KEY, GEMINI_MODEL
    OPENROUTER_API_KEY      المفتاح من https://openrouter.ai/keys
    OPENROUTER_MODEL        موديل واحد أو كذا موديل بفاصلة (بيجرّبهم بالترتيب)، مثال: google/gemini-2.5-flash,openai/gpt-4o-mini
    OPENROUTER_MAX_TOKENS   اختياري (الافتراضي 12000)
    LLM_FALLBACK_COOLDOWN   ثواني البقاء على OpenRouter بعد وقوع Gemini (الافتراضي 300)
"""
from __future__ import annotations

import os
import time

import httpx

from . import envfile

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "google/gemini-2.5-flash"

_state = {"gemini_down_until": 0.0, "last_provider": None, "last_error": None}


class LLMError(RuntimeError):
    pass


def gemini_enabled() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


def openrouter_enabled() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY"))


def enabled() -> bool:
    return gemini_enabled() or openrouter_enabled()


def _mode() -> str:
    m = (os.getenv("LLM_PROVIDER") or "auto").strip().lower()
    return m if m in ("auto", "gemini", "openrouter") else "auto"


def _cooldown() -> float:
    try:
        return max(0.0, float(os.getenv("LLM_FALLBACK_COOLDOWN") or 300))
    except ValueError:
        return 300.0


def _openrouter_models() -> list[str]:
    raw = os.getenv("OPENROUTER_MODEL") or DEFAULT_OPENROUTER_MODEL
    return [m.strip() for m in raw.split(",") if m.strip()]


def providers() -> list[str]:
    """ترتيب المحاولة الحالي حسب الإعدادات وحالة Gemini."""
    mode = _mode()
    if mode == "openrouter":
        order = ["openrouter"]
    elif mode == "gemini":
        order = ["gemini"]
    elif time.time() < _state["gemini_down_until"]:
        order = ["openrouter", "gemini"]  # Gemini واقع: OpenRouter الأول
    else:
        order = ["gemini", "openrouter"]
    ok = {"gemini": gemini_enabled(), "openrouter": openrouter_enabled()}
    return [p for p in order if ok[p]]


def status() -> dict:
    return {
        "mode": _mode(),
        "gemini": gemini_enabled(),
        "openrouter": openrouter_enabled(),
        "active": (providers() or [None])[0],
        "gemini_cooldown_left": max(0, int(_state["gemini_down_until"] - time.time())),
        "last_provider": _state["last_provider"],
        "last_error": _state["last_error"],
    }


def _json_or_text(r: httpx.Response):
    try:
        return r.json()
    except Exception:
        return {"error": {"message": (r.text or "")[:300]}}


def _err_message(d, default: str) -> str:
    e = d.get("error") if isinstance(d, dict) else None
    if isinstance(e, dict):
        return str(e.get("message") or default)
    return str(e or default)


async def _gemini(prompt: str, json_mode: bool) -> str:
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    cfg = {"responseMimeType": "application/json", "temperature": 0.4} if json_mode else {"temperature": 0.5}
    async with httpx.AsyncClient(timeout=180) as c:
        r = await c.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]},
            json={"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": cfg},
        )
    d = _json_or_text(r)
    if r.status_code >= 400:
        raise LLMError(f"Gemini {r.status_code}: {_err_message(d, 'Gemini error')}")
    parts = ((d.get("candidates") or [{}])[0].get("content") or {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    if not text.strip():
        raise LLMError("Gemini رجّع رد فاضي")
    return text


async def _openrouter_one(model: str, prompt: str, json_mode: bool) -> str:
    headers = {
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "http://localhost:8787"),
        "X-Title": os.getenv("OPENROUTER_APP_NAME", "Lesson Lab"),
    }
    full = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4 if json_mode else 0.5,
        "max_tokens": int(os.getenv("OPENROUTER_MAX_TOKENS") or 12000),
    }
    if json_mode:
        full["response_format"] = {"type": "json_object"}
    minimal = {k: v for k, v in full.items() if k not in ("response_format", "max_tokens")}

    async with httpx.AsyncClient(timeout=180) as c:
        r = await c.post(OPENROUTER_URL, headers=headers, json=full)
        if r.status_code == 400:  # بعض الموديلات مابتقبلش response_format أو max_tokens: جرّب بأبسط شكل
            r = await c.post(OPENROUTER_URL, headers=headers, json=minimal)
    d = _json_or_text(r)
    if r.status_code >= 400 or (isinstance(d, dict) and d.get("error") and not d.get("choices")):
        raise LLMError(f"OpenRouter[{model}] {r.status_code}: {_err_message(d, 'OpenRouter error')}")
    msg = ((d.get("choices") or [{}])[0].get("message") or {})
    text = msg.get("content") or ""
    if isinstance(text, list):  # بعض الموديلات بترجّع content كقائمة أجزاء
        text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
    if not str(text).strip():
        raise LLMError(f"OpenRouter[{model}] رجّع رد فاضي")
    return str(text)


async def _openrouter(prompt: str, json_mode: bool) -> str:
    last: Exception | None = None
    for model in _openrouter_models():
        try:
            return await _openrouter_one(model, prompt, json_mode)
        except Exception as e:  # الموديل ده وقع/زحمة: جرّب اللي بعده
            last = e
    raise last or LLMError("OpenRouter: مفيش موديل متحدد (OPENROUTER_MODEL)")


async def complete(prompt: str, json_mode: bool = False) -> str:
    """بيرجّع نص الرد من أول مزوّد شغّال. لو Gemini وقع بيحوّل كامل على OpenRouter."""
    envfile.refresh()  # مفاتيح .env الجديدة (زي OPENROUTER_API_KEY) بتتقرأ من غير ريستارت
    order = providers()
    if not order:
        raise LLMError("ضيف GEMINI_API_KEY أو OPENROUTER_API_KEY في ملف .env")
    errors: list[str] = []
    for p in order:
        try:
            text = await (_gemini if p == "gemini" else _openrouter)(prompt, json_mode)
        except Exception as e:
            msg = str(e) or e.__class__.__name__
            errors.append(f"{p}: {msg}")
            _state["last_error"] = msg
            if p == "gemini" and _mode() == "auto" and openrouter_enabled():
                _state["gemini_down_until"] = time.time() + _cooldown()
                print(f"⚠ Gemini وقع ({msg[:120]}) → تحويل كامل على OpenRouter لمدة {int(_cooldown())} ثانية")
            continue
        if p != _state["last_provider"]:
            print(f"✓ الموديل شغّال عن طريق: {p}")
        _state["last_provider"] = p
        if p == "gemini":
            _state["gemini_down_until"] = 0.0  # Gemini رجع يشتغل
        return text
    raise LLMError(" | ".join(errors))

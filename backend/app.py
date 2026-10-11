import asyncio
import json
import os
import re
import shutil
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)  # الملف له الأولوية على متغيرات النظام

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from . import db, envfile, gemini, llm, tts  # noqa: E402
from .persona.dialects import list_dialects, resolve_dialect_id  # noqa: E402
from .persona.lesson import finalize_spec  # noqa: E402
from .validator import validate_spec  # noqa: E402

LESSONS = ROOT / "lessons"
DIST = ROOT / "client" / "dist"


@asynccontextmanager
async def lifespan(_app):
    db.init()
    moved = db.import_legacy_tts_cache()  # مرة واحدة: ملفات tts-cache/ القديمة -> SQLite
    if moved:
        print(f"✓ اتنقل {moved} ملف صوت من tts-cache/ لقاعدة البيانات ({db.db_path().name})")
    yield


app = FastAPI(title="Lesson Lab", lifespan=lifespan)


def err(msg: str, code: int = 400):
    return JSONResponse({"error": msg}, status_code=code)


async def body(req: Request) -> dict:
    try:
        d = await req.json()
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def read_lesson(lid):
    if not re.fullmatch(r"[\w-]+", lid or ""):
        return None
    f = LESSONS / f"{lid}.json"
    return json.loads(f.read_text("utf-8")) if f.exists() else None


@app.get("/api/health")
def health():
    envfile.refresh()
    return {"ok": True, "tts_voice": tts.voice_id(), "tts_model": os.getenv("CARTESIA_MODEL"), "gemini": llm.gemini_enabled(), "openrouter": llm.openrouter_enabled(), "llm": llm.status(),
            "cartesia": tts.enabled(), "tts_cache": db.audio_stats()}


@app.get("/api/dialects")
def dialects():
    return {"default": resolve_dialect_id(os.getenv("NARRATION_DIALECT")), "options": list_dialects()}


def is_modern(l: dict) -> bool:
    """الدرس بالطريقة الجديدة = حكاية من الحياة (هوك + استخدام في الحياة) + أسئلة التأكد."""
    return bool((l.get("story_arc") or {}).get("hook") and l.get("story") and l.get("quiz"))


@app.get("/api/lessons")
def lessons():
    out = []
    for f in sorted(LESSONS.glob("*.json")):
        l = json.loads(f.read_text("utf-8"))
        out.append({"id": l["id"], "title": l["title"], "modern": is_modern(l)})
    return out


@app.get("/api/lessons/{lid}")
def lesson(lid: str):
    l = read_lesson(lid)
    return l if l else err("الدرس مش موجود", 404)


NO_LLM = "ضيف GEMINI_API_KEY أو OPENROUTER_API_KEY في ملف .env الأول"
_regen_lock = None  # بيتعمل أول مرة جوه الـ event loop (متوافق مع Python 3.9)


def regen_lock():
    global _regen_lock
    if _regen_lock is None:
        _regen_lock = asyncio.Lock()
    return _regen_lock


async def make_spec(source: str, is_topic: bool, dialect: str):
    """بيولّد Spec بالطريقة الجديدة (حكاية + هوك + أسئلة) ويفحصه، ويعيد المحاولة مرتين. بيرجّع (spec, errors)."""
    errors: list = []
    for _ in range(2):
        try:
            spec = await gemini.generate_spec(source, errors, is_topic, dialect)
        except json.JSONDecodeError:
            errors = ["الرد مش JSON صالح: رجّع JSON واحد بس من غير أي كلام قبله أو بعده"]
            continue
        finalize_spec(spec, dialect)  # البرسونا + اللهجة (الكود هو اللي بيحددهم مش الموديل)
        ok, errors = validate_spec(spec)
        if ok:
            return spec, []
    return None, errors


@app.post("/api/generate")
async def generate(req: Request):
    if not gemini.enabled():
        return err(NO_LLM)
    b = await body(req)
    topic = str(b.get("topic") or "").strip()[:200]
    text = str(b.get("text") or "").strip()
    if not topic and len(text) < 40:
        return err("اكتب اسم الدرس، أو الصق نص الدرس (40 حرف على الأقل)")
    try:
        dialect = resolve_dialect_id(b.get("dialect") or os.getenv("NARRATION_DIALECT"))
    except ValueError as e:
        return err(str(e))
    try:
        spec, errors = await make_spec(topic or text, bool(topic), dialect)
        if spec is None:
            return err("الموديل طلّع Spec غير صالح: " + " | ".join(errors), 422)
        spec["id"] = f"lesson-{int(time.time() * 1000)}"
        (LESSONS / f"{spec['id']}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), "utf-8")
        return spec
    except Exception as e:
        return err(str(e), 500)


def lesson_source_text(l: dict) -> str:
    """بيجمّع محتوى الدرس القديم (العنوان + شرح الأجزاء + المعمل) كنص مصدر لإعادة شرحه."""
    lines = [f"عنوان الدرس: {l['title']}", "", "محتوى الدرس:"]
    for p in l.get("parts") or []:
        lines.append(f"- {p.get('label', '')}: {p.get('narration', '')}")
    lab = l.get("lab") or {}
    if lab:
        ctl = "، ".join(str(c.get("label", c.get("id"))) for c in lab.get("controls") or [])
        out = "، ".join(f"{o.get('label', o.get('id'))} = {o.get('formula', '')}" for o in (lab.get("model") or {}).get("outputs") or [])
        lines += ["", f"المعمل: المتغيرات ({ctl}) والنواتج ({out})"]
    for c in l.get("checks") or []:
        lines.append(f"سؤال تنبؤ: {c.get('question', '')}")
    return "\n".join(lines)


@app.post("/api/regenerate")
async def regenerate(req: Request):
    """بيعيد شرح درس موجود بالطريقة الجديدة (نفس الـ id ونفس العنوان) وبيحتفظ بنسخة من القديم في lessons/_backup/."""
    if not gemini.enabled():
        return err(NO_LLM)
    b = await body(req)
    old = read_lesson(b.get("lessonId"))
    if not old:
        return err("الدرس مش موجود", 404)
    try:
        dialect = resolve_dialect_id(b.get("dialect") or old.get("dialect") or os.getenv("NARRATION_DIALECT"))
    except ValueError as e:
        return err(str(e))
    async with regen_lock():  # درس واحد في المرة عشان مانكتبش فوق بعض
        try:
            spec, errors = await make_spec(lesson_source_text(old), False, dialect)
            if spec is None:
                return err("الموديل طلّع Spec غير صالح: " + " | ".join(errors), 422)
            spec["id"], spec["title"] = old["id"], old["title"]
            backup = LESSONS / "_backup"
            backup.mkdir(exist_ok=True)
            shutil.copy2(LESSONS / f"{old['id']}.json", backup / f"{old['id']}.{int(time.time())}.json")
            (LESSONS / f"{old['id']}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), "utf-8")
            return {"id": spec["id"], "title": spec["title"], "modern": True}
        except Exception as e:
            return err(str(e), 500)


@app.post("/api/ask")
async def ask(req: Request):
    b = await body(req)
    l = read_lesson(b.get("lessonId"))
    if not l:
        return err("الدرس مش موجود", 404)
    part = next((p for p in l["parts"] if p["id"] == b.get("partId")), None)
    if not gemini.enabled():
        if part:
            return {"answer": f"المدرس الذكي غير مفعل بعد. وهذا ملخص عن {part['label']}: {part.get('simple_narration') or part['narration']}"}
        return {"answer": "المدرس الذكي غير مفعل. أضف GEMINI_API_KEY أو OPENROUTER_API_KEY في ملف .env."}
    try:
        return {"answer": await gemini.ask_tutor(l, part, b.get("labState"), str(b.get("question") or "")[:500])}
    except Exception as e:
        return err(str(e), 500)


@app.post("/api/tts")
async def tts_endpoint(req: Request):
    text = str((await body(req)).get("text") or "").strip()[:1500]
    if not text:
        return err("النص فاضي")
    try:
        lang = str((await body(req)).get("lang") or "")
        lang = lang if re.fullmatch(r"[a-z]{2,3}", lang) else None
        audio = await tts.synthesize(text, lang)
        return Response(audio, media_type="audio/mpeg", headers={"X-Voice-Id": tts.voice_id()})
    except tts.TTSError as e:
        return err(str(e), e.status)
    except Exception as e:
        return err(str(e), 500)


# الواجهة المبنية
if (DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")


@app.get("/{path:path}")
def spa(path: str):
    if (DIST / "index.html").exists():
        f = (DIST / path).resolve()
        if path and f.is_file() and DIST.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html")
    return HTMLResponse(
        "<h2 dir='rtl'>الـ API شغال، بس الواجهة لسه متبنتش.</h2>"
        "<p dir='rtl'>سطّب Node.js وشغّل <code>python main.py</code> تاني، أو انسخ مجلد <code>dist</code> جاهز جوه <code>client/</code>.</p>",
        status_code=200,
    )

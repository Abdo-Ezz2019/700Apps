#!/usr/bin/env python3
"""
مختبر الدرس (Python / FastAPI) - ملف تشغيل واحد.

    python main.py          يسطّب المكتبات، يجهّز الواجهة، ويشغّل المشروع على http://localhost:8787
    python main.py --dev    وضع التطوير (reload للباك إند + Vite للواجهة، محتاج Node)
    python main.py --setup  تجهيز بس من غير تشغيل

Node.js مطلوب مرة واحدة بس لبناء الواجهة (client/dist). لو عندك مجلد dist جاهز
حطه جوه client/ ومش محتاج Node خالص.
"""
import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLIENT = ROOT / "client"
REQUIRED = ["fastapi", "uvicorn", "httpx", "dotenv"]
NODE, NPM = shutil.which("node"), shutil.which("npm")


def die(msg):
    sys.exit(f"\n✗ {msg}")


def run(cmd, cwd):
    print(f"→ {Path(cmd[0]).name} {' '.join(cmd[1:])}   ({cwd.name})")
    if subprocess.call(cmd, cwd=cwd) != 0:
        die(f"الأمر فشل في {cwd.name}")


def ensure_deps():
    if any(importlib.util.find_spec(m) is None for m in REQUIRED):
        print("→ بسطّب مكتبات بايثون…")
        run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], ROOT)
    print("✓ مكتبات بايثون جاهزة")


def ensure_env():
    env = ROOT / ".env"
    if env.exists():
        return
    text = (ROOT / ".env.example").read_text("utf-8")
    if sys.stdin.isatty():
        print("المفاتيح اختيارية (اضغط Enter للتخطّي). من غيرها بيشتغل درس قانون أوم بصوت المتصفح.")
        for key, label in [("GEMINI_API_KEY", "Gemini API key"), ("CARTESIA_API_KEY", "Cartesia API key"), ("CARTESIA_VOICE_ID", "Cartesia voice id")]:
            val = input(f"{label}: ").strip()
            text = text.replace(f"{key}=", f"{key}={val}", 1)
    env.write_text(text, "utf-8")
    print("✓ اتعمل ملف .env")


FREE_MODEL = "gemini-3.5-flash"


def env_get(text, key):
    m = re.search(rf"^{key}=(.*)$", text, re.M)
    return m.group(1).strip() if m else ""


def env_set(text, key, val):
    if re.search(rf"^{key}=.*$", text, re.M):
        return re.sub(rf"^{key}=.*$", lambda _: f"{key}={val}", text, flags=re.M)
    return text.rstrip("\n") + f"\n{key}={val}\n"


def check_gemini_model():
    """موديلات Pro مالهاش free tier (بتديك quota limit: 0). بنقترح Flash المجاني."""
    env = ROOT / ".env"
    text = env.read_text("utf-8")
    model, key = env_get(text, "GEMINI_MODEL"), env_get(text, "GEMINI_API_KEY")
    if not key or "pro" not in model.lower() or env_get(text, "GEMINI_ALLOW_PRO") == "1":
        return
    print(f"⚠ الموديل {model} من فئة Pro ومالوش free tier، فهيرجّع خطأ quota إلا لو مفعّل Billing.")
    if not sys.stdin.isatty():
        return print(f"  غيّر GEMINI_MODEL في .env لـ {FREE_MODEL} (أو GEMINI_ALLOW_PRO=1 لو مفعّل الدفع).")
    ans = input(f"أغيّره لـ {FREE_MODEL} (مجاني)؟ [Y/n]: ").strip().lower()
    if ans in ("", "y", "yes", "ن", "نعم"):
        env.write_text(env_set(text, "GEMINI_MODEL", FREE_MODEL), "utf-8")
        print(f"✓ GEMINI_MODEL={FREE_MODEL}")
    else:
        env.write_text(env_set(text, "GEMINI_ALLOW_PRO", "1"), "utf-8")
        print("تمام، هسيبه زي ما هو ومش هسألك تاني.")


def needs_build():
    index = CLIENT / "dist" / "index.html"
    if not index.exists():
        return True
    built = index.stat().st_mtime
    srcs = [CLIENT / "index.html", *(CLIENT / "src").rglob("*")]
    return any(s.is_file() and s.stat().st_mtime > built for s in srcs)


def build_client():
    has_dist = (CLIENT / "dist" / "index.html").exists()
    if not (NODE and NPM):
        if not has_dist:
            print("⚠ Node.js مش متسطّب ومفيش client/dist، فالـ API هيشتغل من غير واجهة.\n"
                  "  سطّب Node من https://nodejs.org أو انسخ مجلد dist جاهز جوه client/")
        return
    if not needs_build():
        print("✓ الواجهة جاهزة")
        return
    if not (CLIENT / "node_modules").is_dir():
        run([NPM, "install", "--no-audit", "--no-fund"], CLIENT)
    run([NPM, "run", "build"], CLIENT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dev", action="store_true")
    ap.add_argument("--setup", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()

    if sys.version_info < (3, 9):
        die("محتاج Python 3.9 أو أحدث")
    ensure_deps()
    ensure_env()
    check_gemini_model()

    vite = None
    if a.dev:
        if not (NODE and NPM):
            die("وضع --dev محتاج Node.js")
        if not (CLIENT / "node_modules").is_dir():
            run([NPM, "install", "--no-audit", "--no-fund"], CLIENT)
    else:
        build_client()
    if a.setup:
        return print("✓ جاهز. شغّل: python main.py")

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=True)
    port = int(os.getenv("PORT") or 8787)
    url = f"http://localhost:{5173 if a.dev else port}"
    if not a.no_browser:
        threading.Timer(3 if a.dev else 2, lambda: webbrowser.open(url)).start()

    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    if a.dev:
        vite = subprocess.Popen([NPM, "run", "dev"], cwd=CLIENT)
    print(f"\n✓ شغّال على {url}   (اضغط Ctrl+C للإيقاف)\n")
    import uvicorn
    try:
        uvicorn.run("backend.app:app", host="127.0.0.1", port=port, reload=a.dev,
                    reload_dirs=[str(ROOT / "backend")] if a.dev else None)
    finally:
        if vite and vite.poll() is None:
            vite.terminate()


if __name__ == "__main__":
    main()

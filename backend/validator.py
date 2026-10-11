"""يتأكد إن الـ Lesson Spec سليم قبل ما يوصل للواجهة."""
import re

from .arabic import strip_deep
from .persona.dialects import find_dialect_leaks

SAFE_FORMULA = re.compile(r"^[\w+\-*/().\s]+$")
ANIM_OPS = {"show", "hide", "pulse", "bounce", "wiggle", "move", "count", "set_text"}


def sanitize_svg(svg: str) -> str:
    svg = re.sub(r"<script[\s\S]*?</script>", "", str(svg), flags=re.I)
    svg = re.sub(r"<foreignObject[\s\S]*?</foreignObject>", "", svg, flags=re.I)
    svg = re.sub(r"<image[\s\S]*?>", "", svg, flags=re.I)
    svg = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*')", "", svg, flags=re.I)
    return re.sub(r"javascript:", "", svg, flags=re.I)


def validate_spec(spec):
    """بترجّع (ok, errors) وبتنظّف الـ SVG جوه الـ spec."""
    errors = []
    if not isinstance(spec, dict):
        return False, ["الـ Spec مش object"]
    for k in list(spec):  # لو Gemini حط تشكيل أو تنوين غصب عنه، بنشيله من كل النصوص
        spec[k] = strip_deep(spec[k])
    if not spec.get("title"):
        errors.append("title ناقص")

    scene = spec.get("scene") or {}
    svg = scene.get("svg")
    if not isinstance(svg, str) or not svg.strip().startswith("<svg"):
        errors.append("scene.svg لازم يبدأ بـ <svg")
        svg = None
    else:
        svg = scene["svg"] = sanitize_svg(svg)

    parts = spec.get("parts")
    if not isinstance(parts, list) or not parts:
        errors.append("parts لازم يكون فيه جزء واحد على الأقل")
    else:
        seen = set()
        for p in parts:
            pid = p.get("id")
            if not (pid and p.get("label") and p.get("narration")):
                errors.append(f"جزء ناقص (id/label/narration): {pid!r}")
            if pid in seen:
                errors.append(f"id مكرر: {pid}")
            seen.add(pid)
            if svg and pid and not re.search(rf"data-part-id=[\"']{re.escape(pid)}[\"']", svg):
                errors.append(f'الجزء "{pid}" مالوش data-part-id في الـ SVG')

    lab = spec.get("lab")
    if lab:
        controls = lab.get("controls")
        if not isinstance(controls, list) or not controls:
            errors.append("lab.controls ناقصة")
        else:
            for c in controls:
                if not re.fullmatch(r"[A-Za-z_]\w*", c.get("id") or ""):
                    errors.append(f"control id غير صالح: {c.get('id')}")
                if not all(isinstance(c.get(k), (int, float)) for k in ("min", "max")):
                    errors.append(f"min/max لازم أرقام: {c.get('id')}")
        for o in (lab.get("model") or {}).get("outputs", []):
            if not SAFE_FORMULA.match(o.get("formula") or ""):
                errors.append(f"formula غير آمنة: {o.get('id')}")
        fp = (lab.get("visual") or {}).get("flow_path")
        if fp and svg and f"id='{fp}'" not in svg and f'id="{fp}"' not in svg:
            errors.append(f"flow_path مش موجود في الـ SVG: {fp}")

    # الحكاية + سؤال التأكد من الفهم
    story = spec.get("story")
    if not isinstance(story, list) or len(story) < 3:
        errors.append("story لازم يكون فيها 3 فقرات على الأقل [{text, part}]")
    else:
        ids = {p.get("id") for p in parts if isinstance(p, dict)} if isinstance(parts, list) else set()
        for b in story:
            if not (isinstance(b, dict) and str(b.get("text") or "").strip()):
                errors.append("فقرة في الـ story ناقصة (text)")
            elif b.get("part") and b["part"] not in ids:
                errors.append(f"story.part مش موجود في parts: {b['part']}")
    if isinstance(story, list) and svg:
        svg = scene["svg"] = _repair_anims(story, svg)  # تصليح تلقائي قبل الفحص (الأنيميشن اختياري)
        errors += _check_anims(story, svg)
    quiz = spec.get("quiz")
    opts = quiz.get("options") if isinstance(quiz, dict) else None
    if not (isinstance(quiz, dict) and quiz.get("question") and quiz.get("explanation")
            and isinstance(opts, list) and len(opts) >= 2
            and isinstance(quiz.get("answer"), int) and 0 <= quiz["answer"] < len(opts)):
        errors.append("quiz ناقص (question/options/answer/explanation) أو answer خارج الاختيارات")
    elif isinstance(story, list) and not (isinstance(quiz.get("retell"), int) and 0 <= quiz["retell"] < len(story)):
        quiz["retell"] = 0

    for c in spec.get("checks") or []:
        if not (c.get("question") and isinstance(c.get("options"), list) and isinstance(c.get("answer"), int)):
            errors.append("check ناقص")

    errors += _check_persona(spec, story)
    errors += _check_dialect(spec)
    return not errors, errors


def _wrap_part_id(svg: str, pid: str) -> str:
    """لو الجزء pid ليه data-part-id بس مالوش id: بنلف محتواه في <g id='pid'> (من غير ما نلمس مجموعة الجزء نفسها)."""
    if not re.fullmatch(r"[A-Za-z_][\w-]*", pid or ""):
        return svg
    m = re.search(rf"<g\b[^>]*data-part-id=[\"']{re.escape(pid)}[\"'][^>]*>", svg)
    if not m or m.group(0).endswith("/>"):
        return svg
    depth = 1
    for t in re.finditer(r"<g\b[^>]*>|</g\s*>", svg[m.end():]):
        tok = t.group(0)
        if tok.startswith("</"):
            depth -= 1
            if depth == 0:
                close = m.end() + t.start()
                return svg[:m.end()] + f"<g id='{pid}'>" + svg[m.end():close] + "</g>" + svg[close:]
        elif not tok.endswith("/>"):
            depth += 1
    return svg


def _repair_anims(story, svg: str) -> str:
    """بيصلّح مراجع الأنيميشن اللي الموديل بيغلط فيها:
    - عنصر مذكور في anim وليه data-part-id بس من غير id  -> بنضيفله id بلف محتواه.
    - عنصر مش موجود في الـ SVG خالص -> بنشيله من الخطوة، ولو الخطوة فضيت بنشيلها (الحكاية بتتحكي عادي من غير الحركة دي).
    الأخطاء التانية (خطوة غير معروفة، ids ناقصة...) لسه بتتفحص في _check_anims."""
    def ids_in(x):
        return set(re.findall(r"""\sid=[\"']([^\"']+)[\"']""", x))

    known = ids_in(svg)
    for b in story:
        if not isinstance(b, dict) or not isinstance(b.get("anim"), list):
            continue
        for st in b["anim"]:
            if isinstance(st, dict):
                refs = list(st.get("ids") or []) if isinstance(st.get("ids"), list) else ([st["id"]] if st.get("id") else [])
                refs += [st[k] for k in ("to", "label") if isinstance(st.get(k), str)]
                for r in refs:
                    if isinstance(r, str) and r not in known:
                        svg = _wrap_part_id(svg, r)
    known = ids_in(svg)
    for b in story:
        if not isinstance(b, dict) or not isinstance(b.get("anim"), list):
            continue
        kept = []
        for st in b["anim"]:
            if not isinstance(st, dict) or st.get("do") not in ANIM_OPS:
                kept.append(st)  # بيتفحص ويتبلّغ عنه في _check_anims
                continue
            if isinstance(st.get("ids"), list):
                st["ids"] = [i for i in st["ids"] if i in known]
                if not st["ids"]:
                    continue
            elif st.get("id") is not None and st["id"] not in known:
                continue
            if any(isinstance(st.get(k), str) and st[k] not in known for k in ("to", "label")):
                continue
            kept.append(st)
        b["anim"] = kept
    return svg


def _check_anims(story, svg):
    """يتأكد إن خطوات الأنيميشن في الحكاية بتشاور على عناصر موجودة فعلًا في الـ SVG."""
    svg_ids = set(re.findall(r"""\sid=["']([^"']+)["']""", svg))
    errs, total = [], 0
    for n, b in enumerate(story, 1):
        if not isinstance(b, dict):
            continue
        steps = b.get("anim") or []
        if not isinstance(steps, list):
            errs.append(f"story[{n}].anim لازم يبقى list")
            b["anim"] = []
            continue
        clean = []
        for st in steps:
            if not isinstance(st, dict) or st.get("do") not in ANIM_OPS:
                errs.append(f"story[{n}]: خطوة أنيميشن غير معروفة {st!r} (المسموح: {sorted(ANIM_OPS)})")
                continue
            try:
                st["at"] = min(1.0, max(0.0, float(st.get("at") or 0)))
            except (TypeError, ValueError):
                st["at"] = 0.0
            ids = st.get("ids") if isinstance(st.get("ids"), list) else ([st["id"]] if st.get("id") else [])
            refs = list(ids)
            if st["do"] == "move" and st.get("to"):
                refs.append(st["to"])
            if st["do"] == "count" and st.get("label"):
                refs.append(st["label"])
            if not ids:
                errs.append(f"story[{n}].{st['do']}: لازم ids أو id")
            if st["do"] == "move" and not (st.get("to") or isinstance(st.get("by"), list)):
                errs.append(f"story[{n}].move: لازم to أو by")
            if st["do"] == "set_text" and "text" not in st:
                errs.append(f"story[{n}].set_text: text ناقص")
            for r in refs:
                if r not in svg_ids:
                    errs.append(f"story[{n}].{st['do']}: العنصر '{r}' مالوش id في الـ SVG")
            clean.append(st)
        b["anim"] = clean
        total += len(clean)
    return errs  # الأنيميشن اختياري: الحكاية حكاية من الحياة، والرسمة بتتحرك بس لما الحدث ظاهر فيها


PERSONA_ROLES = {"in_story_character", "in_world_narrative_voice"}

# عبارات الشرح/المحاضرة: ممنوعة جوه الحكاية (الشرح مكانه part.narration والـ quiz والـ checks)
LECTURE_PHRASES = [
    "سنتعلم", "سوف نتعلم", "سنتعرف", "هنتعلم", "هنتعرف", "بنتعلم", "تعالوا نتعلم", "تعال نتعلم", "نتعلم اليوم",
    "تعلمنا", "درس اليوم", "درسنا", "في علم", "في الرياضيات", "في العلوم", "في الحساب نسمي",
    "نسمي", "نسمي هذا", "نسمي ذلك", "يسمى", "تسمى", "بنسمي", "بنسميه", "بنسميها", "اسمه العلمي",
    "تعريف", "القاعدة", "تذكر أن", "تذكروا أن", "لاحظ أن", "لاحظوا أن", "الخلاصة",
]
_AR_WORDS = re.compile("[\u0621-\u064A]+")


def _norm(t: str) -> str:
    t = re.sub("[\u064B-\u065F\u0670\u0640]", "", str(t))
    return re.sub("[\u0623\u0625\u0622]", "\u0627", t)


def find_lecture_phrases(text: str) -> list:
    """بيدوّر على عبارات شرح جاهزة جوه نص الحكاية (بعد توحيد الألف وشيل التشكيل)."""
    padded = " " + " ".join(_AR_WORDS.findall(_norm(text))) + " "
    return [p for p in LECTURE_PHRASES if f" {' '.join(_AR_WORDS.findall(_norm(p)))} " in padded]


def _check_persona(spec, story):
    """فحوصات البرسونا والحكاية من حزمة Darb (persona_*, story_arc, setup/payoff)."""
    errs = []
    p = spec.get("persona")
    if not isinstance(p, dict):
        errs.append("persona_missing: لازم persona")
    else:
        if p.get("teaching_role") is not False:
            errs.append("persona_teacher_role: teaching_role لازم يكون false (البرسونا مش مدرس)")
        if p.get("role") not in PERSONA_ROLES:
            errs.append("persona_role_invalid")
        if not str(p.get("voice") or "").strip():
            errs.append("persona_voice_missing")
        if spec.get("dialect") and p.get("dialect") != spec["dialect"]:
            errs.append("persona.dialect لازم يطابق dialect الدرس")
    arc = spec.get("story_arc")
    if not isinstance(arc, dict):
        errs.append("story_arc ناقص (world, goal, conflict, resolution)")
    else:
        for k in ("world", "goal", "conflict", "resolution", "hook", "life_use"):
            if not str(arc.get(k) or "").strip():
                errs.append(f"story_arc.{k} ناقص" + (" (الموقف اللي بيشد الطالب في أول جملة)" if k == "hook" else " (موقف من حياة الطفل بيفيد فيه الدرس)" if k == "life_use" else ""))
    if isinstance(story, list) and story and all(isinstance(b, dict) for b in story):
        if story[0].get("story_function") != "setup":
            errs.append("أول فقرة في الحكاية لازم story_function = setup (موقف مفتوح وسؤال، من غير تلخيص)")
        first = str(story[0].get("text") or "")
        if "؟" not in first and "?" not in first:
            errs.append("أول فقرة لازم تبقى هوك: موقف بيشد الانتباه من أول جملة وينتهي بسؤال مفتوح (علامة ؟)")
        for n, b in enumerate(story, 1):
            hits = find_lecture_phrases(b.get("text", ""))
            if hits:
                errs.append(f"story[{n}]: الحكاية مش بتشرح الدرس، شيل عبارات الشرح دي: {', '.join(hits)}")
        if story[-1].get("story_function") != "payoff":
            errs.append("آخر فقرة لازم story_function = payoff (تجاوب على سؤال الهوك وتبيّن إزاي الدرس فادنا في حياتنا)")
    return errs


def _check_dialect(spec):
    """كلمات من قايمة avoid بتاعة اللهجة: صوت البرسونا بلهجة الدرس، وطبقة الشرح دايمًا فصحى بسيطة."""
    d = spec.get("dialect")
    if not d or d == "english":
        return []
    story = spec.get("story") if isinstance(spec.get("story"), list) else []
    reactions = ((spec.get("lab") or {}).get("reactions") or []) if isinstance(spec.get("lab"), dict) else []
    voice = [b.get("text", "") for b in story if isinstance(b, dict)] + [r.get("say", "") for r in reactions if isinstance(r, dict)]

    expl = []
    for pt in spec.get("parts") or []:
        if isinstance(pt, dict):
            expl += [pt.get("label", ""), pt.get("narration", ""), pt.get("simple_narration", "")]
    quiz = spec.get("quiz") if isinstance(spec.get("quiz"), dict) else {}
    expl += [quiz.get("question", ""), quiz.get("explanation", "")] + [str(o) for o in quiz.get("options", [])]
    for c in spec.get("checks") or []:
        if isinstance(c, dict):
            expl += [c.get("question", ""), c.get("explanation", "")] + [str(o) for o in c.get("options", [])]

    errs = []
    leaks = find_dialect_leaks(voice, d)
    if leaks:
        errs.append(f"كلمات من لهجة تانية في صوت الحكاية ({d}): {', '.join(leaks)}")
    leaks = find_dialect_leaks(expl, "msa")
    if leaks:
        errs.append(f"كلمات عامية في طبقة الشرح (لازم فصحى بسيطة): {', '.join(leaks)}")
    return errs

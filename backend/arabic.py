"""تنظيف النص العربي قبل الصوت: بنشيل التشكيل والتنوين والتطويل نهائيًا."""
import re

# فتحة/ضمة/كسرة/سكون/شدّة/تنوين (064B-065F) + ألف خنجرية + علامات القرآن + التطويل
_MARKS = re.compile("[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED\u08D3-\u08E1\u08E3-\u08FF\u0640]")


def strip_tashkeel(text: str) -> str:
    return _MARKS.sub("", text) if isinstance(text, str) else text


def strip_deep(obj):
    """بيشيل التشكيل من كل النصوص جوه dict/list (للـ Lesson Spec)."""
    if isinstance(obj, str):
        return strip_tashkeel(obj)
    if isinstance(obj, list):
        return [strip_deep(x) for x in obj]
    if isinstance(obj, dict):
        return {k: strip_deep(v) for k, v in obj.items()}
    return obj

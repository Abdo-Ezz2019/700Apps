"""ربط حزمة البرسونا بالـ Lesson Spec: بيضيف persona/dialect/language ويظبّط story_arc وstory_function."""
from __future__ import annotations

from typing import Any

from .dialects import get_dialect, tts_language
from .persona_engine import build_persona

STRATEGIES = {"MYSTERY", "CHALLENGE", "MISSION", "DISCOVERY", "PROBLEM", "PREDICTION", "INVESTIGATION", "JOURNEY", "SIMULATION", "CUSTOM"}
STORY_FUNCTIONS = {"setup", "discovery", "investigation", "learner_decision", "resolution", "payoff"}


def finalize_spec(spec: Any, dialect: str | None = None) -> Any:
    """بيتنادى بعد ما Gemini يرجّع الـ Spec وقبل الفحص. الكود هو اللي بيحدد dialect/language/persona مش الموديل."""
    if not isinstance(spec, dict):
        return spec
    profile = get_dialect(dialect)

    arc = spec.get("story_arc") if isinstance(spec.get("story_arc"), dict) else None
    if arc is not None:
        strategy = str(arc.get("strategy") or "DISCOVERY").upper()
        arc["strategy"] = strategy if strategy in STRATEGIES else "CUSTOM"
        spec["story_arc"] = arc

    supplied = spec.get("persona") if isinstance(spec.get("persona"), dict) else {}
    outline = {
        "persona": supplied,
        "story_goal": str((arc or {}).get("goal") or ""),
    }
    spec["persona"] = build_persona(outline, None, profile["id"])  # teaching_role=False دايمًا
    spec["dialect"] = profile["id"]
    spec["language"] = profile["language_code"]
    spec["direction"] = profile["direction"]
    spec["tts_language"] = tts_language(profile["id"])

    story = spec.get("story")
    if isinstance(story, list):
        last = len(story) - 1
        for i, b in enumerate(story):
            if isinstance(b, dict):
                f = str(b.get("story_function") or "").strip().lower()
                if f not in STORY_FUNCTIONS:
                    f = "setup" if i == 0 else "payoff" if i == last else "discovery"
                b["story_function"] = f
    return spec

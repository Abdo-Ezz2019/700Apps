"""توليد الدروس + المدرس الذكي (Gemini مع تحويل أوتوماتيك لـ OpenRouter)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from . import llm
from .arabic import strip_tashkeel
from .persona.prompt_builder import build_prompt

LESSONS = Path(__file__).resolve().parent.parent / "lessons"


def enabled() -> bool:
    """فيه موديل متاح؟ (Gemini أو OpenRouter)"""
    return llm.enabled()


async def _call(prompt: str, json_mode: bool = False) -> str:
    # Gemini أساسي، ولو وقع بيتحوّل كامل على OpenRouter (شوف backend/llm.py)
    return await llm.complete(prompt, json_mode)


def _parse_json(t: str):
    t = re.sub(r"^```(?:json)?", "", t.strip(), flags=re.I)
    t = re.sub(r"```$", "", t).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        a, b = t.find("{"), t.rfind("}")  # موديلات OpenRouter ساعات بتحط كلام قبل/بعد الـ JSON
        if a != -1 and b > a:
            return json.loads(t[a:b + 1])
        raise


def _example() -> str:
    ex = json.loads((Path(__file__).resolve().parent / "example_lesson.json").read_text("utf-8"))
    ex.pop("id", None)
    ex["scene"]["svg"] = (
        "<svg viewBox='0 0 600 320'>... كل جزء داخل <g data-part-id='ID'> ... "
        "والعناصر اللي هتتحرّك ليها id (a1..a8, f1..f5, num, eq) وبعضها opacity='0' في الأول، "
        "وأماكن الوصول دوائر مش ظاهرة زي <circle id='s6' cx='382' cy='160' r='2' fill='none'/> ... </svg>"
    )
    return json.dumps(ex, ensure_ascii=False, indent=1)


# المنهج والبرسونا واللهجة والقواعد العامة: من حزمة Darb (backend/persona). هنا بس الشكل التقني للـ Spec.
SCHEMA_RULES = """OUTPUT SCHEMA AND TECHNICAL RULES
- Top-level keys: title, persona, story_arc, scene, parts, lab, checks, story, quiz. The keys id, dialect, language and direction are added by code: do not write them.
- title: a short neutral lesson title (label layer).
- persona: {name (optional), identity, voice, emotional_beat}. English instruction data, never shown to the student. Leave out name and identity when a plain narrator tells the story. Never write teaching_role.
- story_arc: {strategy: MYSTERY|CHALLENGE|MISSION|DISCOVERY|PROBLEM|PREDICTION|INVESTIGATION|JOURNEY|SIMULATION|CUSTOM, world, premise, hook (what grabs the student in the first sentence), life_use (the everyday situation where this lesson's idea helps), goal, conflict, resolution}. English instruction data, never shown to the student.
- scene.svg: draw the everyday world of the story (the same objects the character uses, so the picture matches the story) with the lesson's concepts as clickable parts inside it. A single <svg viewBox='0 0 600 320'>, single quotes for attributes, NO script, event handlers, images or foreignObject. Clear, friendly, colorful shapes with short <text> labels in the lesson language (font-family='Cairo', fill='#14213d', pointer-events='none').
- Every concept the student can click is a <g data-part-id='ID'> wrapping its shapes, with a matching entry in "parts". Use 4 to 8 parts.
- ANIMATABLE OBJECTS: anything the story will animate needs its own unique id attribute (latin letters/digits, e.g. <g id='a1'>); repeated objects get one id each (a1, a2, a3 ...). Animate elements INSIDE a part group, never the data-part-id group itself. Objects that should appear later start hidden with the attribute opacity='0'. For exact destinations use invisible target markers such as <circle id='s6' cx='382' cy='160' r='2' fill='none'/> (a move goes to the center of the target). Any number/equation text the animation changes gets an id (e.g. id='num', id='eq') and a starting text. Make each object's bounding box centered on its main shape (e.g. add an invisible <circle r='24' fill='none'/> inside the group).
- COUNTING AND ARITHMETIC topics (counting, addition, subtraction, multiplication, division, fractions, money, time...): the picture MUST use real countable objects (apples in a basket, fingers of a hand, coins, candies, pencils, blocks) and whenever a beat counts or calculates inside the character's real situation, the character counts ALOUD while the picture counts with it: addition = new objects pop in or move into the basket and are counted; subtraction = objects move out or disappear and the rest are counted again; a hand whose fingers pop up one by one is great for small numbers. For other topics (science, geography, health...) animate the real process step by step as the story reaches it: things appear, arrows or objects move, labels change.
- parts: [{id (latin lowercase), label, narration (explanation layer, 2-4 short sentences), simple_narration (one short sentence), highlight {zoom: 1.2-1.8}}].
- lab: only if the lesson has a quantitative relationship, otherwise null. controls[{id (valid JS identifier), label, min, max, step, default}], model.outputs[{id,label,unit,formula using control ids and + - * / ( ) only}], reactions[{when:{control,change:'increase'|'decrease'} or {output,above}, say}] (the persona's short reaction, persona voice), optional visual{flow_path: id of an SVG <path> in the scene, speed_output, speed_scale, glow: id of an SVG element, glow_output, glow_max}. Keep control ranges small and kid-friendly and make sure no output can become negative.
- checks: 1-2 prediction questions [{question, options (3), answer (index), explanation}] (explanation layer).
- story: 4 to 6 beats in order, [{story_function, text, part, anim}]. story_function is one of setup | discovery | investigation | learner_decision | resolution | payoff; the FIRST beat is "setup" and it is the HOOK (a gripping unresolved moment that ends with an open question, with a question mark), and the LAST beat is "payoff" (it answers the hook question and shows how the lesson's idea helped in real life). text = the persona voice, 2 to 4 short spoken sentences (about 20 to 45 words), written to be read aloud smoothly. THE STORY NEVER EXPLAINS THE LESSON: no definitions, rules, formulas, vocabulary lists, steps of the lesson, or phrases such as \"we will learn\", \"we learned\", \"in math we call this\"; the idea only shows up in what the character does or realizes in a real daily-life situation. The whole story is narrated beat after beat WITHOUT stopping, so never address the reader with "press next" or "wait". part = the id of the part to zoom on during that beat (or null).
- anim = OPTIONAL steps that play WHILE the beat is spoken, only for events that really happen in the drawing (use [] for a beat whose event is not in the picture, and then part may be null; never force the drawing to illustrate something it does not contain): [{at, do, ...}]. at is 0..1 = how far into the beat's narration the step starts: at = (position of the word where it should start, counting words from 1) / (number of words in the beat). Step types: show{ids, stagger} (pops in), hide{ids, stagger}, pulse{ids}, bounce{ids, stagger} (happy hop), wiggle{ids, stagger} (shake), move{id, to:<target id>} (flies in an arc and lands with a bounce) or move{id, by:[dx,dy]}, count{ids, label:<id of a text element>, from (default 1)}, set_text{id, text}. stagger = seconds between items (0.1 to 0.5). A beat that has anim should have 1 to 3 steps (a move, show or count, plus a bounce, wiggle or pulse for emphasis when it fits). A count step needs NO stagger: it automatically follows the voice, one object per spoken number, so start it (at) exactly on the first number word and write the numbers as separate words in the text. The picture's state carries over: things shown, moved or changed in earlier beats stay that way later. Every id used in anim must exist in the SVG.
- quiz: ONE comprehension question asked right after the story (explanation layer): {question, options (3), answer (index), explanation, retell (index of the story beat to replay if the student answers wrong)}. It must be a NEW simple everyday situation (different from the story) that needs the same idea, with numbers written as words, 2 plausible wrong options, and it must differ from the "checks" questions.
- Keep the same JSON shape as the example.
@@ERRORS@@

EXAMPLE (its persona, story_arc and story show the expected voice; metadata is English, learner text follows the language policy):
@@EXAMPLE@@

@@LABEL@@
@@INPUT@@"""

TOPIC_LABEL = (
    "TOPIC (the student only gave a topic name: first write accurate, very simple lesson content for 4th and 5th grade "
    "primary students about it yourself, then build the spec from that content):"
)


def default_dialect() -> str:
    from .persona.dialects import resolve_dialect_id
    return resolve_dialect_id(os.getenv("NARRATION_DIALECT"))


def build_generation_prompt(text: str, previous_errors=None, is_topic: bool = False, dialect: str | None = None) -> str:
    errs = ("Fix these validation errors from the previous attempt:\n- " + "\n- ".join(previous_errors)) if previous_errors else ""
    base = build_prompt("lesson_spec_compiler", dialect)  # البرسونا + المنهج + سياسة اللغة
    return (base + "\n\n" + SCHEMA_RULES).replace("@@ERRORS@@", errs).replace("@@EXAMPLE@@", _example()) \
        .replace("@@LABEL@@", TOPIC_LABEL if is_topic else "LESSON:").replace("@@INPUT@@", text)


async def generate_spec(text: str, previous_errors=None, is_topic: bool = False, dialect: str | None = None):
    return _parse_json(await _call(build_generation_prompt(text, previous_errors, is_topic, dialect), True))


async def ask_tutor(lesson: dict, part, lab_state, question: str) -> str:
    part_txt = f"{part['label']} - {part['narration']}" if part else "no part selected"
    persona = lesson.get("persona") or {}
    arc = lesson.get("story_arc") or {}
    prompt = (
        build_prompt("tutor_answer", lesson.get("dialect"))
        + f"\n\nLESSON TITLE: {lesson['title']}"
        + (f"\nSTORY CHARACTER (you may mention by name): {persona['name']}" if persona.get("name") else "")
        + (f"\nSTORY GOAL: {arc['goal']}" if arc.get("goal") else "")
        + f"\nSELECTED PART: {part_txt}\nCURRENT LAB VALUES: {json.dumps(lab_state or {}, ensure_ascii=False)}\nCHILD'S QUESTION: {question}"
    )
    return strip_tashkeel((await _call(prompt)).strip())

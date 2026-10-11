"""Dialect/language selection for Darb narration.

Profiles live in dialect_profiles.json (edit that file to tune a dialect).
Supported ids: "egyptian", "saudi", "msa", "english".
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PROFILES_PATH = Path(__file__).with_name("dialect_profiles.json")


def _load() -> dict[str, Any]:
    return json.loads(_PROFILES_PATH.read_text(encoding="utf-8"))


_DATA = _load()
DEFAULT_DIALECT: str = _DATA["default"]


def list_dialects() -> list[str]:
    return list(_DATA["dialects"].keys())


def resolve_dialect_id(name: str | None) -> str:
    """Accept ids and common aliases (e.g. 'ksa', 'fusha', 'en', 'ar-EG'). None -> default."""
    if not name:
        return DEFAULT_DIALECT
    key = str(name).strip().lower().replace(" ", "_")
    resolved = _DATA["aliases"].get(key)
    if resolved is None:
        raise ValueError(f"Unknown dialect {name!r}. Choose one of: {', '.join(list_dialects())}")
    return resolved


def get_dialect(name: str | None = None) -> dict[str, Any]:
    return _DATA["dialects"][resolve_dialect_id(name)]


def dialect_policy_block(name: str | None = None) -> str:
    """Text block appended to a system prompt so the model writes in the chosen dialect."""
    d = get_dialect(name)
    shared = _DATA["shared_rules"]
    lines = [
        f"LANGUAGE POLICY (selected: {d['label']}, code {d['language_code']})",
        f"- Narration and dialogue: {d['narration']}",
        f"- Captions, explanations, labels: {d['captions_explanations']}",
        f"- Terminology: {shared['terminology']}",
    ]
    lines.append("- Student address: " + (shared["student_address_english"] if d["id"] == "english" else shared["student_address_arabic"]))
    lines.append("- Prefer: " + "; ".join(d["prefer"]))
    lines.append("- Avoid: " + "; ".join(d["avoid"]))
    for extra in ("no_diacritics", "spoken_numbers"):  # project additions
        if shared.get(extra):
            lines.append(f"- {extra.replace('_', ' ').capitalize()}: " + shared[extra])
    lines.append("- Consistency: " + shared["consistency"])
    lines.append("- Output format: " + shared["json_keys"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Project additions (not in the original pack)
# ---------------------------------------------------------------------------
import re  # noqa: E402

_AR_LETTERS = re.compile("[\u0621-\u064A]+")


def _norm_ar(word: str) -> str:
    """Strip diacritics and unify alef forms so 'إيه' and 'ايه' compare equal."""
    word = re.sub("[\u064B-\u065F\u0670\u0640]", "", word)
    return re.sub("[\u0623\u0625\u0622]", "\u0627", word)


def tts_language(name: str | None = None) -> str:
    """Language code to send to the TTS engine ('ar' for every Arabic option, 'en' for English)."""
    return get_dialect(name).get("tts_language") or get_dialect(name)["language_code"].split("-")[0]


def find_dialect_leaks(texts: list[str], name: str | None = None) -> list[str]:
    """Words from the dialect's avoid-list (see forbidden_words in the profile) that appear in `texts`."""
    forbidden = {_norm_ar(w) for w in get_dialect(name).get("forbidden_words", [])}
    if not forbidden:
        return []
    found: list[str] = []
    for t in texts:
        for tok in _AR_LETTERS.findall(str(t)):
            n = _norm_ar(tok)
            # also catch a one-letter conjunction prefix: وايه / فده
            hit = n in forbidden or (len(n) > 2 and n[0] in "\u0648\u0641" and n[1:] in forbidden)
            if hit and tok not in found:
                found.append(tok)
    return found

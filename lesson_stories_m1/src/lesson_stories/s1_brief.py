"""S1 Localization Brief: cached LLM call + schema/count validation + reviewer pass, with retries."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from . import config, prompts
from .cache import BriefCache, make_key, utcnow
from .errors import ErrorCode, PipelineError
from .llm import TASK_BRIEF, TASK_BRIEF_REVIEW, LLMClient
from .models import Brief

STAGE = "S1"
_STR_LISTS = ("names_female", "names_male", "places", "foods", "transport",
              "holidays_and_seasons", "sensitivities", "family_terms")
_STR_FIELDS = ("school_context", "clothing_norms", "humor_notes")


def _is_str_list(v: Any) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)


def validate_brief_dict(d: Any) -> List[str]:
    """Schema and count checks (the blockers). Returns a list of human-readable problems; [] = valid."""
    if not isinstance(d, dict):
        return ["brief must be a JSON object"]
    errs: List[str] = []

    for name in _STR_LISTS:
        v = d.get(name)
        if not _is_str_list(v):
            errs.append(f"{name} must be a list of non-empty strings")
        elif name in config.BRIEF_MIN_COUNTS and len(v) < config.BRIEF_MIN_COUNTS[name]:
            errs.append(f"{name} has {len(v)} items, need at least {config.BRIEF_MIN_COUNTS[name]}")
    for name in _STR_FIELDS:
        if not isinstance(d.get(name), str) or not d[name].strip():
            errs.append(f"{name} must be a non-empty string")

    humor = d.get("humor_notes")
    if isinstance(humor, str) and humor.strip():
        sentences = [s for s in re.split(r"[.!?؟۔]+", humor) if s.strip()]
        if not 1 <= len(sentences) <= 2:
            errs.append(f"humor_notes must be 1 to 2 sentences, got {len(sentences)}")

    cur = d.get("currency")
    if not isinstance(cur, dict):
        errs.append("currency must be an object")
    else:
        for k in ("code", "symbol", "spoken_name"):
            if not isinstance(cur.get(k), str) or not cur[k].strip():
                errs.append(f"currency.{k} must be a non-empty string")
        prices = cur.get("typical_prices")
        if (not isinstance(prices, list)
                or not all(isinstance(p, dict) and isinstance(p.get("item"), str)
                           and isinstance(p.get("price"), str) for p in prices)):
            errs.append("currency.typical_prices must be a list of {item, price}")
        elif len(prices) != config.BRIEF_TYPICAL_PRICES:
            errs.append(f"currency.typical_prices has {len(prices)} items, need exactly "
                        f"{config.BRIEF_TYPICAL_PRICES}")

    ss = d.get("speech_style")
    if not isinstance(ss, dict):
        errs.append("speech_style must be an object")
    else:
        if not isinstance(ss.get("guidance"), str) or not ss["guidance"].strip():
            errs.append("speech_style.guidance must be a non-empty string")
        ex = ss.get("example_phrases")
        if not _is_str_list(ex):
            errs.append("speech_style.example_phrases must be a list of strings")
        elif len(ex) != config.BRIEF_EXAMPLE_PHRASES:
            errs.append(f"speech_style.example_phrases has {len(ex)} items, need exactly "
                        f"{config.BRIEF_EXAMPLE_PHRASES}")
    return errs


def review_flags(raw: Dict[str, Any], llm: LLMClient) -> List[str]:
    """Second LLM call. Returns a list of flag descriptions; [] means the brief passes."""
    answer = llm.complete_json(TASK_BRIEF_REVIEW, prompts.brief_review_prompt(), {"brief": raw})
    flags = answer.get("flags") if isinstance(answer, dict) else None
    if not isinstance(flags, list):
        return ["reviewer returned a malformed answer"]
    out = []
    for f in flags:
        if isinstance(f, dict):
            out.append(f"reviewer flagged {f.get('field', '?')}: {f.get('item', '')} ({f.get('issue', '')})")
        else:
            out.append(f"reviewer flagged: {f}")
    return out


def run(country: str, language: str, dialect_applied: Optional[str], age_group: str,
        llm: LLMClient, db: sqlite3.Connection, now: Optional[datetime] = None,
        ttl_days: int = config.BRIEF_TTL_DAYS,
        max_attempts: int = config.MAX_STAGE_ATTEMPTS) -> Brief:
    """Return the brief: from cache if fresh, otherwise generate -> validate -> review -> cache.

    On a blocker or a reviewer flag the LLM is called again with the problems as feedback.
    After `max_attempts` the stage fails with BRIEF_INVALID or BRIEF_REVIEW_FLAGGED.
    """
    now = now or utcnow()
    cache = BriefCache(db)
    key = make_key(country, language, dialect_applied, age_group)

    cached = cache.get(key, now)
    if cached is not None:
        return Brief.from_dict(cached)

    feedback: List[str] = []
    last_code, last_problems = ErrorCode.BRIEF_INVALID, ["no attempt made"]
    for _ in range(max_attempts):
        raw = llm.complete_json(
            TASK_BRIEF,
            prompts.brief_prompt(country, language, dialect_applied, age_group, feedback),
            {"country": country, "language": language, "dialect": dialect_applied,
             "age_group": age_group, "feedback": list(feedback)},
        )
        problems = validate_brief_dict(raw)
        if problems:
            feedback, last_code, last_problems = problems, ErrorCode.BRIEF_INVALID, problems
            continue
        flags = review_flags(raw, llm)
        if flags:
            feedback, last_code, last_problems = flags, ErrorCode.BRIEF_REVIEW_FLAGGED, flags
            continue
        cache.put(key, raw, ttl_days, now)
        return Brief.from_dict(raw)

    raise PipelineError(last_code, "; ".join(last_problems), STAGE)

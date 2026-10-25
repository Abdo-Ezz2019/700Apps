"""S0 Intake: normalize, locate the topic, build context, check language, pick dialect and duration."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple, Union

from . import config, prompts
from .errors import ErrorCode, PipelineError
from .llm import TASK_TOPIC_LOCATOR, LLMClient
from .models import Intake, PipelineWarning, Request
from .text_utils import find_span, normalize_text

STAGE = "S0"

_ARABIC_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")
_LATIN_RE = re.compile(r"[A-Za-z\u00C0-\u024F]")


def script_ratio(text: str, language: str) -> float:
    """Share of letters in `text` written in the script of `language` (ar -> Arabic, en -> Latin)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    rx = _ARABIC_RE if language == "ar" else _LATIN_RE
    return sum(1 for c in letters if rx.match(c)) / len(letters)


def derive_dialect(country: str) -> str:
    """Country code -> default dialect (EG->egyptian, SA->gulf, ..., else msa)."""
    return config.COUNTRY_DIALECT.get(country.upper(), config.DEFAULT_DIALECT)


def resolve_dialect(language: str, country: str, requested: Optional[str],
                    tts_supported_dialects: List[str],
                    tts_provider_name: str = "groq") -> Tuple[Optional[str], List[PipelineWarning]]:
    """Return (dialect_applied, warnings). English -> (None, []). Falls back to msa with DIALECT_FALLBACK."""
    if language != "ar":
        return None, []
    if requested and requested not in config.DIALECTS:
        raise PipelineError(ErrorCode.INVALID_REQUEST, f"unknown dialect '{requested}'", STAGE)
    wanted = requested or derive_dialect(country)
    if wanted == "msa" or wanted in tts_supported_dialects:
        return wanted, []
    origin = "requested" if requested else f"derived from country {country}"
    msg = (f"Dialect '{wanted}' ({origin}) is not supported by TTS provider "
           f"'{tts_provider_name}'; using 'msa'.")
    return "msa", [PipelineWarning("DIALECT_FALLBACK", msg)]


def resolve_duration(age_group: str, requested: Optional[int]) -> int:
    """Requested value or the age default, clamped to the age range."""
    prof = config.AGE_GROUPS.get(age_group)
    if prof is None:
        raise PipelineError(ErrorCode.INVALID_REQUEST, f"unknown age_group '{age_group}'", STAGE)
    value = requested if requested is not None else prof.default_sec
    return max(prof.min_sec, min(prof.max_sec, int(value)))


def _locate_topic(req: Request, lesson_text: str, llm: LLMClient) -> Tuple[str, Optional[Tuple[int, int]]]:
    """Return (topic_text, span-in-lesson_text or None)."""
    if req.topic_text and req.topic_text.strip():
        topic_text = normalize_text(req.topic_text).strip()
        # Only used to find the surrounding context; the text itself is taken as given.
        return topic_text, find_span(lesson_text, topic_text, topic_text)

    answer: Dict[str, Any] = llm.complete_json(
        TASK_TOPIC_LOCATOR,
        prompts.topic_locator_prompt(req.topic_title),
        {"lesson_text": lesson_text, "topic_title": req.topic_title},
    )
    span = find_span(lesson_text, str(answer.get("start_quote", "")), str(answer.get("end_quote", "")))
    if span is None:
        raise PipelineError(ErrorCode.TOPIC_NOT_FOUND,
                            f"could not locate topic '{req.topic_title}' in lesson_text", STAGE)
    return lesson_text[span[0]:span[1]].strip(), span


def _context(lesson_text: str, span: Optional[Tuple[int, int]]) -> Tuple[str, str]:
    """(prior_text, later_preview); partial words at the cut edges are dropped."""
    if span is None:
        return "", ""
    start, end = span
    lo = max(0, start - config.PRIOR_CONTEXT_CHARS)
    prior = lesson_text[lo:start]
    if lo > 0 and " " in prior:
        prior = prior.split(None, 1)[1] if len(prior.split(None, 1)) > 1 else prior
    hi = end + config.LATER_PREVIEW_CHARS
    later = lesson_text[end:hi]
    if hi < len(lesson_text) and " " in later:
        later = later.rsplit(None, 1)[0]
    return prior.strip(), later.strip()


def run(request: Union[Request, Dict[str, Any]], tts_supported_dialects: List[str],
        llm: LLMClient, tts_provider_name: str = "groq") -> Intake:
    """Run S0 and return the `intake.json` content. Raises PipelineError on failure."""
    req = request if isinstance(request, Request) else Request.from_dict(request)
    if req.language not in config.SUPPORTED_LANGUAGES:
        raise PipelineError(ErrorCode.INVALID_REQUEST, f"unsupported language '{req.language}'", STAGE)

    lesson_text = normalize_text(req.lesson_text)                       # 1
    topic_text, span = _locate_topic(req, lesson_text, llm)             # 2
    if len(topic_text) < config.MIN_TOPIC_CHARS:                        # 3
        raise PipelineError(ErrorCode.INPUT_TOO_SHORT,
                            f"topic_text has {len(topic_text)} chars, need {config.MIN_TOPIC_CHARS}", STAGE)
    prior_text, later_preview = _context(lesson_text, span)             # 4
    if script_ratio(topic_text, req.language) < config.SCRIPT_RATIO_MIN:  # 5
        raise PipelineError(ErrorCode.LANGUAGE_MISMATCH,
                            f"topic_text is not mostly {req.language} script", STAGE)
    dialect, warnings = resolve_dialect(req.language, req.country, req.dialect,   # 6
                                        tts_supported_dialects, tts_provider_name)
    duration = resolve_duration(req.age_group, req.target_duration_sec)  # 7

    return Intake(
        topic_title=req.topic_title, topic_text=topic_text, prior_text=prior_text,
        later_preview=later_preview, language=req.language, dialect_applied=dialect,
        country=req.country, age_group=req.age_group, grade=req.grade, subject=req.subject,
        target_duration_sec=duration, warnings=warnings,
    )

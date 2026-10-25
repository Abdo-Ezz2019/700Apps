"""Plain dataclasses for the request and the two artifacts (intake.json, brief.json)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .errors import ErrorCode, PipelineError


@dataclass
class PipelineWarning:
    code: str
    message: str


@dataclass
class Request:
    lesson_id: str
    lesson_text: str
    topic_title: str
    country: str
    language: str
    age_group: str
    topic_id: Optional[str] = None
    topic_text: Optional[str] = None  # `topic.text`
    dialect: Optional[str] = None
    grade: Optional[str] = None
    subject: Optional[str] = None
    target_duration_sec: Optional[int] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Request":
        topic = d.get("topic") or {}
        missing = [k for k in ("lesson_text", "country", "language", "age_group")
                   if not d.get(k)]
        if not topic.get("title"):
            missing.append("topic.title")
        if missing:
            raise PipelineError(ErrorCode.INVALID_REQUEST,
                                f"missing fields: {', '.join(missing)}", "S0")
        grade = d.get("grade")
        return cls(
            lesson_id=str(d.get("lesson_id", "")),
            lesson_text=d["lesson_text"],
            topic_title=topic["title"],
            topic_id=topic.get("topic_id"),
            topic_text=topic.get("text"),
            country=str(d["country"]).upper(),
            language=str(d["language"]).lower(),
            dialect=(str(d["dialect"]).lower() if d.get("dialect") else None),
            age_group=str(d["age_group"]),
            grade=(str(grade) if grade is not None else None),
            subject=d.get("subject"),
            target_duration_sec=d.get("target_duration_sec"),
        )


@dataclass
class Intake:
    """Artifact `intake.json`."""
    topic_title: str
    topic_text: str
    prior_text: str
    later_preview: str
    language: str
    dialect_applied: Optional[str]
    country: str
    age_group: str
    grade: Optional[str]
    subject: Optional[str]
    target_duration_sec: int
    warnings: List[PipelineWarning] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Price:
    item: str
    price: str


@dataclass
class Currency:
    code: str
    symbol: str
    spoken_name: str
    typical_prices: List[Price]


@dataclass
class SpeechStyle:
    guidance: str
    example_phrases: List[str]


@dataclass
class Brief:
    """Artifact `brief.json`."""
    names_female: List[str]
    names_male: List[str]
    currency: Currency
    places: List[str]
    foods: List[str]
    transport: List[str]
    holidays_and_seasons: List[str]
    sensitivities: List[str]
    school_context: str
    clothing_norms: str
    family_terms: List[str]
    humor_notes: str
    speech_style: SpeechStyle

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Brief":
        c = d["currency"]
        s = d["speech_style"]
        return cls(
            names_female=list(d["names_female"]),
            names_male=list(d["names_male"]),
            currency=Currency(
                code=c["code"], symbol=c["symbol"], spoken_name=c["spoken_name"],
                typical_prices=[Price(p["item"], p["price"]) for p in c["typical_prices"]],
            ),
            places=list(d["places"]),
            foods=list(d["foods"]),
            transport=list(d["transport"]),
            holidays_and_seasons=list(d["holidays_and_seasons"]),
            sensitivities=list(d["sensitivities"]),
            school_context=d["school_context"],
            clothing_norms=d["clothing_norms"],
            family_terms=list(d["family_terms"]),
            humor_notes=d["humor_notes"],
            speech_style=SpeechStyle(s["guidance"], list(s["example_phrases"])),
        )

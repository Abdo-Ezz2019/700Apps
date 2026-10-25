"""Prompt builders. Kept separate so they can be tuned without touching stage logic."""
from __future__ import annotations

from typing import List, Optional

from . import config


def topic_locator_prompt(topic_title: str) -> str:
    return (
        "You are given a lesson and a topic title. Locate where the topic starts and ends.\n"
        f"Topic title: {topic_title}\n"
        "Return ONLY JSON: {\"start_quote\": str, \"end_quote\": str}.\n"
        "Each quote must be 6 to 12 words copied VERBATIM from the lesson: "
        "start_quote = the first words of the topic, end_quote = the last words of the topic. "
        "Do not paraphrase and do not include text from neighbouring topics."
    )


def brief_prompt(country: str, language: str, dialect: Optional[str], age_group: str,
                 feedback: Optional[List[str]] = None) -> str:
    m = config.BRIEF_MIN_COUNTS
    p = (
        f"Create a localization brief for kids' educational stories.\n"
        f"Country: {country}; language: {language}; dialect: {dialect or 'n/a'}; age group: {age_group}.\n"
        "Return ONLY JSON with keys: names_female, names_male, currency{code,symbol,spoken_name,"
        "typical_prices[{item,price}]}, places, foods, transport, holidays_and_seasons, sensitivities, "
        "school_context, clothing_norms, family_terms, humor_notes, speech_style{guidance,example_phrases}.\n"
        f"Minimums: names_female>={m['names_female']}, names_male>={m['names_male']}, "
        f"typical_prices=exactly {config.BRIEF_TYPICAL_PRICES}, places>={m['places']}, foods>={m['foods']}, "
        f"transport>={m['transport']}, holidays_and_seasons>={m['holidays_and_seasons']}, "
        f"sensitivities>={m['sensitivities']}, example_phrases=exactly {config.BRIEF_EXAMPLE_PHRASES}, "
        "humor_notes = 1 to 2 sentences.\n"
        "Names: common first names only, no public figures. No real brands. "
        "No stereotypes, no religious or political content."
    )
    if feedback:
        p += "\nYour previous attempt was rejected. Fix ALL of these problems:\n- " + "\n- ".join(feedback)
    return p


def brief_review_prompt() -> str:
    return (
        "Review this localization brief for: stereotypes, religious or political content, "
        "real brands, and real public figures.\n"
        "Return ONLY JSON: {\"flags\": [{\"field\": str, \"item\": str, \"issue\": str}]}. "
        "Return an empty list if nothing is wrong."
    )

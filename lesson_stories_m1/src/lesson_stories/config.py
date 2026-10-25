"""All tunable numbers and lookup tables in one place."""
from __future__ import annotations

from dataclasses import dataclass

# ---- S0 ----
MIN_TOPIC_CHARS = 200
PRIOR_CONTEXT_CHARS = 2500
LATER_PREVIEW_CHARS = 400
SCRIPT_RATIO_MIN = 0.60

SUPPORTED_LANGUAGES = ("ar", "en")
DIALECTS = ("egyptian", "gulf", "levantine", "maghrebi", "msa")


@dataclass(frozen=True)
class AgeProfile:
    min_sec: int
    default_sec: int
    max_sec: int


# 9-11 comes from the spec (default 150, range 120-210).
# 6-8 and 12-14 are ASSUMPTIONS (see docs/DECISIONS.md) - replace with Section 1 values.
AGE_GROUPS = {
    "6-8": AgeProfile(90, 120, 150),
    "9-11": AgeProfile(120, 150, 210),
    "12-14": AgeProfile(150, 210, 300),
}

COUNTRY_DIALECT = {
    "EG": "egyptian",
    **{c: "gulf" for c in ("SA", "AE", "KW", "QA", "BH", "OM", "YE", "IQ")},
    **{c: "levantine" for c in ("JO", "LB", "SY", "PS")},
    **{c: "maghrebi" for c in ("MA", "DZ", "TN", "LY")},
}
DEFAULT_DIALECT = "msa"

# ---- S1 ----
BRIEF_TTL_DAYS = 90
MAX_STAGE_ATTEMPTS = 3  # first try + 2 retries with feedback

BRIEF_MIN_COUNTS = {
    "names_female": 20,
    "names_male": 20,
    "places": 8,
    "foods": 6,
    "transport": 3,
    "holidays_and_seasons": 4,
    "sensitivities": 3,
}
BRIEF_TYPICAL_PRICES = 6
BRIEF_EXAMPLE_PHRASES = 5

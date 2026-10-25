"""Text helpers: normalization and diacritic-insensitive quote search (`norm_ar`)."""
from __future__ import annotations

import re
import unicodedata
from typing import List, Optional, Tuple

_ALEF_FOLD = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"}
_YA_FOLD = {"ى": "ي"}
_TRAILING_PUNCT = ".!?؟۔…\"'»”)"


def normalize_text(text: str) -> str:
    """S0 step 1: Unicode NFC, NBSP -> space, collapse 3+ newlines into 2. Diacritics are kept."""
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\n{3,}", "\n\n", text)


def _norm_with_map(text: str) -> Tuple[str, List[int]]:
    """Normalize for searching and keep, for every output char, its index in `text`.

    Drops diacritics/tatweel/format marks, folds alef and ya variants, maps Arabic-Indic
    digits to ASCII, lowercases Latin, and turns every run of punctuation/whitespace
    into one space.
    """
    out: List[str] = []
    idx: List[int] = []
    for i, ch in enumerate(text):
        cat = unicodedata.category(ch)
        if cat in ("Mn", "Cf") or ch == "ـ":
            continue
        if ch.isalnum():
            if ch.isdigit():
                ch = str(unicodedata.digit(ch, 0)) if not ch.isascii() else ch
            ch = _ALEF_FOLD.get(ch, _YA_FOLD.get(ch, ch)).lower()
            out.append(ch)
            idx.append(i)
        elif out and out[-1] != " ":
            out.append(" ")
            idx.append(i)
    if out and out[-1] == " ":
        out.pop()
        idx.pop()
    return "".join(out), idx


def norm_ar(text: str) -> str:
    """Normalized form used for searching (see `_norm_with_map`)."""
    return _norm_with_map(text)[0]


def find_span(text: str, start_quote: str, end_quote: str) -> Optional[Tuple[int, int]]:
    """Return (start, end) offsets in the ORIGINAL `text`, or None.

    The span runs from the start of `start_quote` to the end of `end_quote`
    (searched from the start position on). Closing punctuation right after the
    end quote (e.g. the final period) is included.
    """
    norm, idx = _norm_with_map(text)
    ns, ne = norm_ar(start_quote or ""), norm_ar(end_quote or "")
    if not ns or not ne:
        return None
    p = norm.find(ns)
    if p < 0:
        return None
    q = norm.find(ne, p)
    if q < 0:
        return None
    start = idx[p]
    end = idx[q + len(ne) - 1] + 1
    while end < len(text) and text[end] in _TRAILING_PUNCT:
        end += 1
    return (start, end) if end > start else None

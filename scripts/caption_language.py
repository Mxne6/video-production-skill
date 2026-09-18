"""Language-aware caption boundary helpers.

This module deliberately has no dependency on the video production engine.  It
only returns safe Python string offsets; it does not assign audio times or
rewrite caption text.
"""

from __future__ import annotations

import unicodedata
from typing import Iterable


# The list is intentionally finite.  A number followed by an arbitrary word
# must not become one protected span merely because that word happens to look
# like a unit in a particular project.
_UNITS = (
    "mmol",
    "g",
    "kHz",
    "MHz",
    "GHz",
    "kPa",
    "MPa",
    "GPa",
    "mPa",
    "mV",
    "kV",
    "MW",
    "kW",
    "mW",
    "mAh",
    "mol",
    "mm",
    "cm",
    "dm",
    "km",
    "mg",
    "kg",
    "lb",
    "lbs",
    "oz",
    "mL",
    "ml",
    "L",
    "Pa",
    "psi",
    "bar",
    "rpm",
    "Hz",
    "kJ",
    "J",
    "kcal",
    "cal",
    "kWh",
    "Wh",
    "W",
    "mA",
    "A",
    "V",
    "m",
    "cm²",
    "m²",
    "cm³",
    "m³",
    "ns",
    "µs",
    "μs",
    "ms",
    "s",
    "min",
    "h",
    "day",
    "days",
    "°C",
    "°F",
    "℃",
    "℉",
    "%",
)
_SORTED_UNITS = tuple(sorted(_UNITS, key=len, reverse=True))
_SIGN_CHARS = "+-−±"


def _is_word_char(char: str) -> bool:
    """Return whether *char* belongs to a lexical word or number token."""

    if not char:
        return False
    # Combining marks can be used for decomposed accented letters.  Treating
    # them as part of the token prevents a cut between ``e`` and its accent.
    return char.isalnum() or char == "_" or unicodedata.category(char).startswith("M")


def _is_internal_punctuation(text: str, index: int, start: int) -> bool:
    char = text[index]
    if char in "'’":
        return index > start and index + 1 < len(text) and _is_word_char(text[index - 1]) and _is_word_char(text[index + 1])
    if char in "-‐‑‒–—":
        return index > start and index + 1 < len(text) and _is_word_char(text[index - 1]) and _is_word_char(text[index + 1])
    if char in ".,":
        if index <= start or index + 1 >= len(text):
            return False
        if text[index - 1].isdigit() and text[index + 1].isdigit():
            return True
        # Keep continuous letter-dot abbreviations such as ``U.S.A`` and
        # ``e.g`` together. A trailing full stop is handled below so that a
        # sentence-final abbreviation is protected as one span too.
        return text[index - 1].isalpha() and text[index + 1].isalpha()
    return False


def _scan_token(text: str, start: int) -> int:
    """Return the end of the lexical token beginning at *start*."""

    end = start + 1
    while end < len(text):
        if _is_word_char(text[end]) or _is_internal_punctuation(text, end, start):
            end += 1
            continue
        break
    return end


def _abbreviation_end(text: str, start: int, token_end: int) -> int:
    """Include a final dot in a continuous letter-dot abbreviation."""

    if token_end >= len(text) or text[token_end] != ".":
        return token_end
    candidate = text[start:token_end]
    pieces = candidate.split(".")
    if len(pieces) < 2 or any(not piece or not piece.isalpha() for piece in pieces):
        return token_end
    return token_end + 1


def _is_number_token(value: str) -> bool:
    return bool(value) and any(char.isdigit() for char in value) and all(char.isdigit() or char in ".," for char in value)


def _unit_at(text: str, start: int) -> int | None:
    """Return the end of a recognized unit at *start*, if any."""

    folded = text[start:].casefold()
    for unit in _SORTED_UNITS:
        candidate = unit.casefold()
        if not folded.startswith(candidate):
            continue
        end = start + len(unit)
        # Do not match ``m`` in ``minutes`` or ``kg`` in ``kgf``.  Symbols such
        # as ℃ and % have no word suffix to guard against.
        if end < len(text) and _is_word_char(text[end]):
            continue
        return end
    return None


def _number_with_unit_end(text: str, start: int, number_end: int) -> int:
    """Return the end of a number/unit span, without swallowing later words."""

    if not _is_number_token(text[start:number_end]):
        return number_end

    # A percent sign is an immediately attached unit.
    if number_end < len(text) and text[number_end] == "%":
        return number_end + 1

    cursor = number_end
    while cursor < len(text) and text[cursor] in " \t\u00a0":
        cursor += 1
    unit_end = _unit_at(text, cursor)
    return unit_end if unit_end is not None else number_end


def _protected_spans(text: str, protected: Iterable[str]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    terms = [term for term in protected if term]
    for term in terms:
        cursor = 0
        while True:
            index = text.find(term, cursor)
            if index < 0:
                break
            spans.append((index, index + len(term)))
            cursor = index + 1

    return spans


def english_boundaries(text: str, protected: list[str]) -> set[int]:
    """Return safe Python offsets for English caption or pause cuts.

    Returned offsets include ``0`` and ``len(text)``.  Interior offsets of
    words, ASCII/curly-apostrophe contractions, hyphenated words, decimal
    numbers, recognized number/unit pairs, and explicit protected terms are
    excluded.  Whitespace and punctuation are left in the original text and
    are not normalized here, so callers can keep exact caption phrases.

    Empty protected terms are ignored.  The function accepts any iterable at
    runtime for convenience, while non-string terms are rejected explicitly.
    """

    if not isinstance(text, str):
        raise TypeError("text must be str")
    if protected is None:
        raise TypeError("protected must be a list[str]")
    try:
        terms = list(protected)
    except TypeError as exc:
        raise TypeError("protected must be an iterable of strings") from exc
    if any(not isinstance(term, str) for term in terms):
        raise TypeError("protected must contain only strings")

    length = len(text)
    if not text:
        return {0}

    spans = _protected_spans(text, terms)

    cursor = 0
    while cursor < length:
        if (
            text[cursor] in _SIGN_CHARS
            and cursor + 1 < length
            and text[cursor + 1].isdigit()
            and (cursor == 0 or not _is_word_char(text[cursor - 1]))
        ):
            number_start = cursor + 1
            token_end = _scan_token(text, number_start)
            token_end = _abbreviation_end(text, number_start, token_end)
            spans.append((cursor, _number_with_unit_end(text, number_start, token_end)))
            cursor = token_end
            continue
        if not _is_word_char(text[cursor]):
            cursor += 1
            continue
        start = cursor
        token_end = _scan_token(text, start)
        token_end = _abbreviation_end(text, start, token_end)
        spans.append((start, _number_with_unit_end(text, start, token_end)))
        cursor = token_end

    boundaries = set(range(length + 1))
    for start, end in spans:
        # The endpoints are safe; only cuts inside a protected/token span are
        # removed.  Overlapping ranges are naturally handled by the union.
        boundaries.difference_update(range(start + 1, end))

    return boundaries


__all__ = ["english_boundaries"]

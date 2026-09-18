"""Explicit language profiles for video narration; translation is out of scope."""
from __future__ import annotations

import unicodedata


DEFAULT_LANGUAGE = 'zh-CN'
SUPPORTED_LANGUAGES = frozenset(('zh-CN', 'en', 'fr-FR'))

_PROFILES = {
    'zh-CN': {'language_boost': 'Chinese', 'voice_id': 'Chinese (Mandarin)_Sincere_Adult'},
    # A system-voice candidate from the official directory; it is not listening-approved.
    'en': {'language_boost': 'English', 'voice_id': 'English_expressive_narrator'},
    'fr-FR': {'language_boost': 'French', 'voice_id': 'French_expressive_narrator'},
}


def normalize_language(value: str | None) -> str:
    """Return an exact supported target-language tag, defaulting to zh-CN."""
    if value is None:
        return DEFAULT_LANGUAGE
    if type(value) is not str or value not in SUPPORTED_LANGUAGES:
        raise ValueError('Unsupported language; use one of: '+', '.join(sorted(SUPPORTED_LANGUAGES)))
    return value


def language_profile(language: str | None) -> dict:
    return _PROFILES[normalize_language(language)].copy()


def language_boost(language: str | None) -> str:
    return language_profile(language)['language_boost']


def default_voice_id(language: str | None) -> str:
    return language_profile(language)['voice_id']


def is_english(language: str | None) -> bool:
    return normalize_language(language) in {'en', 'fr-FR'}


def language_identity(language: str | None) -> str | None:
    """Use a cache discriminator only when it changes historical Chinese output."""
    current = normalize_language(language)
    return None if current == DEFAULT_LANGUAGE else current


def _chinese_units(text: str) -> int:
    return sum(not char.isspace() and not unicodedata.category(char).startswith('P') for char in text)


def _english_words(text: str) -> int:
    """Count English tokens without splitting contractions or decimal values."""
    count = 0
    active = False
    for index, char in enumerate(text):
        next_is_alnum = index + 1 < len(text) and text[index + 1].isalnum()
        if char.isalnum():
            if not active:
                count += 1
            active = True
        elif char in ".'’-" and active and next_is_alnum:
            continue
        else:
            active = False
    return count


def estimate_narration_seconds(text: str, language: str | None) -> list[float]:
    """Return a rough fast-to-slow estimate; real TTS duration remains authoritative."""
    if is_english(language):
        words = _english_words(text)
        return [round(words / (170 / 60), 1), round(words / (130 / 60) + 1, 1)]
    units = _chinese_units(text)
    # Preserve the historical Chinese character-rate estimate exactly.
    return [round(units / 4.5, 1), round(units / 3.5 + 1, 1)]

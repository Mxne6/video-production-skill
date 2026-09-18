"""Select the language-specific XYZCHEM fixed-outro component."""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from language_profiles import is_english as _is_english
from language_profiles import normalize_language as _normalize_language


ROOT = Path(__file__).resolve().parents[1]
CHINESE_LANGUAGE = "zh-CN"
CHINESE_COMPONENT_ID = "xyzchem-fixed-outro-v2"
ENGLISH_COMPONENT_ID = "xyzchem-fixed-outro-en-v1"
FRENCH_COMPONENT_ID = "xyzchem-fixed-outro-fr-v1"

_COMPONENT_FILES = {
    CHINESE_LANGUAGE: "assets/brand/outro/zh-CN/component.json",
    "en": "assets/brand/outro/en/component.json",
    "fr-FR": "assets/brand/outro/fr-FR/component.json",
}
_TEMPLATE_FILES = {
    CHINESE_LANGUAGE: "assets/brand/outro/zh-CN/template.html",
    "en": "assets/brand/outro/en/template.html",
    "fr-FR": "assets/brand/outro/fr-FR/template.html",
}


def normalize_language(value=None) -> str:
    """Use the canonical language profile default and validation."""
    return _normalize_language(value)


def is_english(value=None) -> bool:
    """Return whether a normalized project language is an English variant."""
    return _is_english(normalize_language(value))


def project_language(project_or_data) -> str:
    """Read and normalize a Project or project.json-like mapping."""
    if hasattr(project_or_data, "data"):
        project_or_data = project_or_data.data
    if isinstance(project_or_data, Mapping):
        return normalize_language(project_or_data.get("language"))
    return normalize_language(project_or_data)


def _family(language: str) -> str:
    return language if language in _COMPONENT_FILES else CHINESE_LANGUAGE


def component_path(language_or_project=None) -> Path:
    """Return the immutable component JSON path for a language/project."""
    return ROOT / _COMPONENT_FILES[_family(project_language(language_or_project))]


def template_path(language_or_project=None) -> Path:
    """Return the immutable fixed-template path for a language/project."""
    return ROOT / _TEMPLATE_FILES[_family(project_language(language_or_project))]


def load_component(language_or_project=None) -> dict:
    """Load a fresh language-specific component object from disk."""
    path = component_path(language_or_project)
    return json.loads(path.read_text(encoding="utf-8"))


def expected_component_id(language_or_project=None) -> str:
    language = project_language(language_or_project)
    return {"en": ENGLISH_COMPONENT_ID, "fr-FR": FRENCH_COMPONENT_ID}.get(language, CHINESE_COMPONENT_ID)


def reconstruct_caption(component: Mapping) -> str:
    """Reconstruct canonical narration from caption phrases exactly."""
    phrases = component.get("caption_phrases")
    if not isinstance(phrases, list) or not all(isinstance(x, str) for x in phrases):
        raise ValueError("Brand component caption_phrases must be a list of strings")
    text = "".join(phrases)
    if text != component.get("narration"):
        raise ValueError("Brand component caption_phrases must reconstruct narration exactly")
    return text


def validate_component(component: Mapping, language_or_project=None) -> dict:
    """Validate language identity and fixed copy before using a component."""
    language = project_language(language_or_project)
    expected = expected_component_id(language)
    if component.get("id") != expected:
        raise ValueError("Brand component does not match project language: expected " + expected)
    expected_metadata_language = language if is_english(language) else CHINESE_LANGUAGE
    if component.get("language") not in (None, expected_metadata_language):
        raise ValueError("Brand component language metadata does not match project language")
    reconstruct_caption(component)
    if language in ("en", "fr-FR"):
        expected_narration = {"en": "This product is brought to you by Nanjing Xinyi Synthesis Technology Co., Ltd.", "fr-FR": "Ce produit vous est présenté par Nanjing Xinyi Synthesis Technology Co., Ltd."}[language]
        if component.get("narration") != expected_narration:
            raise ValueError("Fixed-outro narration differs from the canonical candidate")
        if component.get("script_status") not in ("pending_confirmation", "approved"):
            raise ValueError("Fixed-outro script has an unsupported confirmation status")
    return dict(component)

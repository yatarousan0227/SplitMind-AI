"""Helpers for selecting the agent's response language."""

from __future__ import annotations

import re

_JAPANESE_CHAR_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]")
_LATIN_LETTER_RE = re.compile(r"[A-Za-z]")

_LANGUAGE_ALIASES = {
    "ja": "ja",
    "ja-jp": "ja",
    "japanese": "ja",
    "jp": "ja",
    "日本語": "ja",
    "en": "en",
    "en-us": "en",
    "en-gb": "en",
    "english": "en",
    "英語": "en",
}

_EXPLICIT_LANGUAGE_PATTERNS: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = (
    (
        "en",
        (
            re.compile(r"英語(?:で|を)?(?:答えて|返事(?:して)?|返信(?:して)?|話して|対応して)"),
            re.compile(r"英語(?:で|を)?お願い"),
            re.compile(r"\brespond in english\b", re.IGNORECASE),
            re.compile(r"\bin english\b", re.IGNORECASE),
            re.compile(r"\benglish please\b", re.IGNORECASE),
        ),
    ),
    (
        "ja",
        (
            re.compile(r"日本語(?:で|を)?(?:答えて|返事(?:して)?|返信(?:して)?|話して|対応して)"),
            re.compile(r"日本語(?:で|を)?お願い"),
            re.compile(r"\brespond in japanese\b", re.IGNORECASE),
            re.compile(r"\bin japanese\b", re.IGNORECASE),
            re.compile(r"\bjapanese please\b", re.IGNORECASE),
        ),
    ),
)


def normalize_response_language(value: str | None) -> str | None:
    """Normalize a user or UI-provided language label to ``ja`` or ``en``."""
    if value is None:
        return None

    normalized = value.strip().lower().replace("_", "-")
    if not normalized or normalized == "auto":
        return None
    return _LANGUAGE_ALIASES.get(normalized)


def detect_response_language(
    user_message: str,
    preferred_language: str | None = None,
) -> str:
    """Resolve the response language from override, in-text request, or script heuristics."""
    normalized = normalize_response_language(preferred_language)
    if normalized is not None:
        return normalized

    explicit = _extract_explicit_language_request(user_message)
    if explicit is not None:
        return explicit

    text = user_message.strip()
    if not text:
        return "ja"

    if _JAPANESE_CHAR_RE.search(text):
        return "ja"

    latin_letters = len(_LATIN_LETTER_RE.findall(text))
    if latin_letters >= 3:
        return "en"

    return "ja"


def response_language_name(language: str) -> str:
    """Return a display label for prompts and UI."""
    return {
        "ja": "日本語",
        "en": "English",
    }.get(language, "日本語")


def _extract_explicit_language_request(user_message: str) -> str | None:
    """Detect simple user instructions such as '英語で答えて'."""
    for language, patterns in _EXPLICIT_LANGUAGE_PATTERNS:
        for pattern in patterns:
            if pattern.search(user_message):
                return language
    return None

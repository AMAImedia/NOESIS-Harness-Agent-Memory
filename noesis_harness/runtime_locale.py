"""noesis_harness/runtime_locale.py

OS/runtime-level language selection for operator-facing UI strings.

The agent picks its RESPONSE language at runtime (English / Russian),
independent of any documentation duplication. Language choice lives in the
runtime, not in duplicated doc trees.

Borrowed patterns:
  - LoopX: runtime preference store with explicit validation and a stable
    on-disk projection (no mutation of the event log).
  - agentmemory: locale as a per-session projection, never baked into facts.
  - Hermes: operator-facing message tables keyed by language, with a safe
    fallback to the default locale when a key or language is missing.

Constraints (AGENTS.md):
  - stdlib only (json, os, pathlib)
  - no LLM calls
  - Python 3.9+ syntax (no `X | None`, no `match`)
  - append-only / read-only on the harness; only the tiny settings file is
    written when the operator changes the language.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

SUPPORTED_LANGS = ("en", "ru")
DEFAULT_LANG = "en"
SETTINGS_FILENAME = "locale_settings.json"

STRINGS = {
    "en": {
        "status": "Status: {status}",
        "no_events": "No events recorded yet.",
        "prompt": "Operator, choose a language (en/ru): ",
        "lang_set": "Language set to {lang}.",
        "invalid_lang": "Invalid language '{lang}'. Use 'en' or 'ru'.",
    },
    "ru": {
        "status": "Статус: {status}",
        "no_events": "События ещё не записаны.",
        "prompt": "Оператор, выберите язык (en/ru): ",
        "lang_set": "Язык установлен: {lang}.",
        "invalid_lang": "Недопустимый язык '{lang}'. Используйте 'en' или 'ru'.",
    },
}


def _validate_lang(lang):
    if lang not in SUPPORTED_LANGS:
        raise ValueError("unsupported_lang:%s" % lang)
    return lang


class LocaleSettings:
    """Load/save the operator's language preference from a tiny JSON file.

    The settings file is stored at noesis_harness/locale_settings.json by
    default (NOT under docs/). The harness event log is never touched.
    """

    def __init__(self, lang=DEFAULT_LANG, path=None):
        self._lang = _validate_lang(lang)
        self._path = Path(path) if path else None

    @classmethod
    def load(cls, path=None):
        candidate = Path(path) if path else Path(__file__).with_name(SETTINGS_FILENAME)
        if not candidate.exists():
            return cls(DEFAULT_LANG, path)
        try:
            with candidate.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (ValueError, OSError):
            return cls(DEFAULT_LANG, path)
        lang = data.get("lang", DEFAULT_LANG)
        try:
            return cls(lang, path)
        except ValueError:
            return cls(DEFAULT_LANG, path)

    def save(self, path=None):
        target = Path(path) if path else (self._path or Path(__file__).with_name(SETTINGS_FILENAME))
        payload = {"lang": self._lang}
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, target)
        self._path = target
        return target

    def get_lang(self):
        return self._lang

    def set_lang(self, lang):
        _validate_lang(lang)
        self._lang = lang
        return self._lang


def get(key, lang=None):
    """Return the localized string for ``key``.

    Falls back to "en" if ``lang`` is unknown or the key is missing for that
    language, so operator-facing output is never blank.
    """
    table_lang = lang if lang in STRINGS else DEFAULT_LANG
    table = STRINGS.get(table_lang, STRINGS[DEFAULT_LANG])
    return table.get(key, STRINGS[DEFAULT_LANG].get(key, key))


class Responder:
    """Returns localized, formatted operator-facing strings.

    Read-only on the harness; only the settings file is written when the
    operator calls set_lang on the bound LocaleSettings.
    """

    def __init__(self, settings=None, lang=None):
        if settings is None:
            if lang is not None:
                settings = LocaleSettings(lang)
            else:
                settings = LocaleSettings()
        self._settings = settings

    def respond(self, template_key, lang=None, **kwargs):
        active_lang = lang if lang is not None else self._settings.get_lang()
        template = get(template_key, active_lang)
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template

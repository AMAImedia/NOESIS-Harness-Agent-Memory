"""noesis_harness/compact_chat.py

A minimal, deterministic terminal REPL that answers operator queries from the
local append-only memory harness instead of an LLM.

Patterns adapted from:
  - LoopX        (replay projection: current view derived by folding events;
                 runtime preference store written independently of the log)
  - agentmemory  (deterministic, offline term-overlap retrieval; no embeddings)
  - Hermes       (operator-facing message tables keyed by language, with a safe
                 fallback to the default locale)

Design guarantees (see AGENTS.md):
  - stdlib only: argparse, sys, json (indirect via deps). No external deps.
  - Deterministic core: ranking is read-only via
    noesis_harness.recall_augment.rank_events. No LLM call ever happens.
  - Append-only safe: the event log is opened read-only. The REPL never appends
    to it. The only write path is the small locale settings file on /lang.
  - Idempotent write path: LocaleSettings.save uses atomic replace.
  - Python 3.9+ syntax: no `X | None`, no `match`.

Honesty caveat: this is a retrieval demo. Answers are templated, ranked
snippets from the event log, NOT generated text.
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable, List, Optional, Tuple

from .recall_augment import rank_events

# Language-specific operator-facing strings for the chat surface itself.
# The /lang confirmation and invalid-lang messages are re-used from
# runtime_locale.STRINGS via the localize() helper below.
CHAT_STRINGS = {
    "en": {
        "no_match": "No matching memory found for your query.",
        "match_header": "Top recalled snippets:",
        "disclaimer": "Retrieved from the local event log. This is not an LLM-generated answer.",
        "unknown_command": "Unknown command: {cmd}. Try '/lang en|ru' or type a query.",
        "farewell": "Bye.",
    },
    "ru": {
        "no_match": "Подходящих записей в памяти не найдено.",
        "match_header": "Наиболее релевантные фрагменты:",
        "disclaimer": "Получено из локального журнала событий. Это не ответ, сгенерированный LLM.",
        "unknown_command": "Неизвестная команда: {cmd}. Используйте '/lang en|ru' или введите запрос.",
        "farewell": "До свидания.",
    },
}

DEFAULT_LANG = "en"
SUPPORTED_LANGS = ("en", "ru")

# Marker returned by process_input to tell the loop to terminate.
_ACTION_CONTINUE = "continue"
_ACTION_EXIT = "exit"


def localize(lang: str, key: str, **kwargs) -> str:
    """Return a localized chat string, falling back to the default locale.

    The runtime_locale module is imported lazily so that the test suite can
    skip gracefully if it is missing at import time (see AGENTS.md note).
    """
    table = CHAT_STRINGS.get(lang, CHAT_STRINGS[DEFAULT_LANG])
    template = table.get(key, CHAT_STRINGS[DEFAULT_LANG].get(key, key))
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError):
        return template


def _runtime_locale_get(key: str, **kwargs) -> str:
    """Return a localized string from runtime_locale.STRINGS (lazy import)."""
    lang = kwargs.get("lang", DEFAULT_LANG)
    try:
        from . import runtime_locale
    except Exception:  # pragma: no cover - runtime_locale missing
        return localize(lang, key, **kwargs)
    return runtime_locale.get(key, lang).format(**kwargs)


def format_query_answer(query: str, events_path: str, top_k: int, lang: str) -> str:
    """Build a compact, deterministic answer from the top ranked snippets.

    Read-only on the event log. Returns a localized "no match" message when no
    event scores above zero relevance.
    """
    ranked = rank_events(query, events_path, top_k=top_k)
    matches = [item for item in ranked if item.get("score", 0.0) > 0.0]
    if not matches:
        return localize(lang, "no_match")

    lines: List[str] = [localize(lang, "match_header")]
    for index, item in enumerate(matches, start=1):
        lines.append(
            "  {0}. [{1}] {2}".format(index, item.get("type", ""), item.get("snippet", ""))
        )
    lines.append(localize(lang, "disclaimer"))
    return "\n".join(lines)


def process_input(
    line: str,
    settings,
    events_path: str,
    top_k: int = 5,
) -> Tuple[str, str]:
    """Interpret one line of operator input.

    Returns ``(response_text, action)`` where ``action`` is either
    ``_ACTION_CONTINUE`` or ``_ACTION_EXIT``. The only write side effect is the
    locale settings file, persisted through ``settings.save()`` when /lang runs.
    """
    stripped = (line or "").strip()
    lang = settings.get_lang()

    if stripped == "exit":
        return (localize(lang, "farewell"), _ACTION_EXIT)

    if stripped == "":
        return ("", _ACTION_CONTINUE)

    if stripped.startswith("/lang"):
        parts = stripped.split()
        target = parts[1] if len(parts) > 1 else ""
        if target in SUPPORTED_LANGS:
            settings.set_lang(target)
            settings.save()
            return (_runtime_locale_get("lang_set", lang=target), _ACTION_CONTINUE)
        return (
            _runtime_locale_get("invalid_lang", lang=target),
            _ACTION_CONTINUE,
        )

    if stripped.startswith("/"):
        return (localize(lang, "unknown_command", cmd=stripped), _ACTION_CONTINUE)

    return (format_query_answer(stripped, events_path, top_k, lang), _ACTION_CONTINUE)


def repl(
    events_path: str,
    settings,
    top_k: int = 5,
    input_func: Optional[Callable[[], Optional[str]]] = None,
    output_func: Optional[Callable[[str], None]] = None,
) -> int:
    """Run the read-eval-print loop until the operator exits.

    ``input_func`` defaults to ``sys.stdin.readline``-style input; ``output_func``
    defaults to ``print``. Injecting them makes the loop testable without a TTY.
    """
    if input_func is None:
        def input_func():  # pragma: no cover - real stdin path
            try:
                return input()
            except EOFError:
                return None

    if output_func is None:
        output_func = print

    while True:
        line = input_func()
        if line is None:
            break
        response, action = process_input(line, settings, events_path, top_k=top_k)
        if response:
            output_func(response)
        if action == _ACTION_EXIT:
            break
    return 0


def _build_settings(lang: Optional[str], locale_path: Optional[str]):
    """Construct a LocaleSettings (lazy import) from args or disk."""
    from . import runtime_locale

    if locale_path is not None:
        if runtime_locale.Path(locale_path).exists():
            settings = runtime_locale.LocaleSettings.load(locale_path)
        else:
            settings = runtime_locale.LocaleSettings(lang or runtime_locale.DEFAULT_LANG, path=locale_path)
    else:
        settings = runtime_locale.LocaleSettings.load()
        if lang is not None:
            settings.set_lang(lang)
    return settings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="NOESIS compact local-memory chat (no LLM)")
    parser.add_argument("--events", required=True, help="Path to the append-only event log")
    parser.add_argument("--lang", default=None, choices=list(SUPPORTED_LANGS), help="Initial language")
    parser.add_argument("--locale-path", default=None, help="Path for the locale settings file")
    parser.add_argument("--top-k", type=int, default=5, help="Number of snippets to recall")
    args = parser.parse_args(argv)

    settings = _build_settings(args.lang, args.locale_path)
    return repl(args.events, settings, top_k=args.top_k)


__all__ = [
    "main",
    "repl",
    "process_input",
    "format_query_answer",
    "localize",
    "CHAT_STRINGS",
]

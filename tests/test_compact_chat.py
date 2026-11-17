"""tests/test_compact_chat.py

Tests for noesis_harness.compact_chat (deterministic, local-memory REPL).

Honesty caveat: these tests exercise retrieval, never generation. The "chat"
answers are ranked snippets from a temp EventStore log.

Skips gracefully if runtime_locale is unavailable at import time.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest import mock

# Ensure the package root is importable regardless of CWD.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from noesis_harness import compact_chat
from noesis_harness.event_store import EventStore

try:
    from noesis_harness import runtime_locale  # noqa: F401
    _HAVE_LOCALE = True
except Exception:  # pragma: no cover - runtime_locale missing
    _HAVE_LOCALE = False

skip_reason = "runtime_locale.py not present; skipping compact_chat locale tests"


def _make_temp_log():
    """Create a temp append-only log with a few recallable events."""
    handle, path = tempfile.mkstemp(suffix=".jsonl", prefix="compact_chat_")
    os.close(handle)
    store = EventStore(path)
    store.append("note", {"note": "deploy the service to production"})
    store.append("note", {"note": "rollback the deploy when health fails"})
    store.append("fact", {"fact": "the cache key expired at midnight"})
    return path


class CompactChatTest(unittest.TestCase):
    def setUp(self):
        self.events_path = _make_temp_log()
        self.addCleanup(lambda: os.path.exists(self.events_path) and os.remove(self.events_path))

    def _settings(self, lang="en", locale_path=None):
        if not _HAVE_LOCALE:
            self.skipTest(skip_reason)
        return runtime_locale.LocaleSettings(lang, path=locale_path)

    # --- query / retrieval -------------------------------------------------

    def test_query_returns_ranked_snippets(self):
        settings = self._settings()
        out = compact_chat.format_query_answer("deploy", self.events_path, top_k=5, lang="en")
        self.assertIn(compact_chat.localize("en", "match_header"), out)
        self.assertIn("deploy the service", out)
        self.assertIn("rollback the deploy", out)

    def test_query_no_match_localized(self):
        settings = self._settings()
        out = compact_chat.format_query_answer("zzz_nomatch_xyz", self.events_path, top_k=5, lang="en")
        self.assertIn(compact_chat.localize("en", "no_match"), out)

    def test_format_query_answer_filters_zero_score(self):
        settings = self._settings()
        out = compact_chat.format_query_answer("", self.events_path, top_k=5, lang="en")
        self.assertIn(compact_chat.localize("en", "no_match"), out)

    def test_process_input_query_action_continues(self):
        settings = self._settings()
        response, action = compact_chat.process_input("deploy", settings, self.events_path)
        self.assertEqual(action, compact_chat._ACTION_CONTINUE)
        self.assertIn("deploy", response)

    # --- /lang -------------------------------------------------------------

    def test_lang_switch_persists_via_temp_path(self):
        if not _HAVE_LOCALE:
            self.skipTest(skip_reason)
        locale_path = tempfile.mktemp(suffix=".json", prefix="locale_")
        self.addCleanup(lambda: os.path.exists(locale_path) and os.remove(locale_path))
        settings = runtime_locale.LocaleSettings("en", path=locale_path)
        response, action = compact_chat.process_input("/lang ru", settings, self.events_path)
        self.assertEqual(action, compact_chat._ACTION_CONTINUE)
        self.assertIn("ru", response)
        reloaded = runtime_locale.LocaleSettings.load(locale_path)
        self.assertEqual(reloaded.get_lang(), "ru")

    def test_lang_switch_invalid_lang(self):
        if not _HAVE_LOCALE:
            self.skipTest(skip_reason)
        settings = self._settings()
        response, action = compact_chat.process_input("/lang de", settings, self.events_path)
        self.assertEqual(action, compact_chat._ACTION_CONTINUE)
        self.assertIn("de", response)
        self.assertIn("Invalid", response)
        self.assertEqual(settings.get_lang(), "en")

    def test_localized_output_strings_ru(self):
        if not _HAVE_LOCALE:
            self.skipTest(skip_reason)
        settings = runtime_locale.LocaleSettings("ru")
        out = compact_chat.format_query_answer("deploy", self.events_path, top_k=5, lang="ru")
        self.assertIn(compact_chat.localize("ru", "match_header"), out)
        self.assertIn(compact_chat.localize("ru", "disclaimer"), out)

    # --- unknown command / exit -------------------------------------------

    def test_unknown_command_handled(self):
        settings = self._settings()
        response, action = compact_chat.process_input("/frobnicate", settings, self.events_path)
        self.assertEqual(action, compact_chat._ACTION_CONTINUE)
        self.assertIn("/frobnicate", response)

    def test_exit_condition_via_process_input(self):
        settings = self._settings()
        response, action = compact_chat.process_input("exit", settings, self.events_path)
        self.assertEqual(action, compact_chat._ACTION_EXIT)
        self.assertIn(compact_chat.localize("en", "farewell"), response)

    def test_repl_exit_condition(self):
        settings = self._settings()
        lines = ["exit"]
        it = iter(lines)

        def fake_input():
            try:
                return next(it)
            except StopIteration:
                return None

        captured = []
        rc = compact_chat.repl(
            self.events_path, settings, input_func=fake_input, output_func=captured.append
        )
        self.assertEqual(rc, 0)
        self.assertTrue(any(compact_chat.localize("en", "farewell") in c for c in captured))

    # --- no mutation of the event log -------------------------------------

    def test_no_event_log_mutation_on_query(self):
        settings = self._settings()
        before = EventStore(self.events_path).count()
        for _ in range(3):
            compact_chat.format_query_answer("deploy", self.events_path, top_k=5, lang="en")
        after = EventStore(self.events_path).count()
        self.assertEqual(before, after)

    def test_no_event_log_mutation_on_lang_switch(self):
        if not _HAVE_LOCALE:
            self.skipTest(skip_reason)
        locale_path = tempfile.mktemp(suffix=".json", prefix="locale_")
        self.addCleanup(lambda: os.path.exists(locale_path) and os.remove(locale_path))
        settings = runtime_locale.LocaleSettings("en", path=locale_path)
        before = EventStore(self.events_path).count()
        compact_chat.process_input("/lang ru", settings, self.events_path)
        after = EventStore(self.events_path).count()
        self.assertEqual(before, after)

    def test_repl_runs_multiple_queries(self):
        settings = self._settings()
        lines = ["deploy", "cache", "exit"]
        it = iter(lines)

        def fake_input():
            try:
                return next(it)
            except StopIteration:
                return None

        captured = []
        rc = compact_chat.repl(
            self.events_path, settings, input_func=fake_input, output_func=captured.append
        )
        self.assertEqual(rc, 0)
        joined = "\n".join(captured)
        self.assertIn("deploy the service", joined)
        self.assertIn("cache key expired", joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)

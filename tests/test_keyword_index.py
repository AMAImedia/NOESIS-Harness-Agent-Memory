"""tests/test_keyword_index.py

Unit tests for noesis_harness/keyword_index.py (read-only inverted keyword
index over the append-only event log). Stdlib only; Python 3.9+ syntax.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from noesis_harness.keyword_index import build, search

FIXTURE_EVENTS = [
    {
        "event_id": "e1",
        "type": "note",
        "payload": {"text": "Alpha beta gamma", "tag": "Alpha"},
        "seq": 1,
    },
    {
        "event_id": "e2",
        "type": "note",
        "payload": {"text": "Beta gamma delta", "tag": "beta"},
        "seq": 2,
    },
    {
        "event_id": "e3",
        "type": "task",
        "payload": {"text": "Gamma delta EPSILON", "n": 7},
        "seq": 3,
    },
]


def _write_log(events, tmp_dir, name="events.jsonl"):
    path = os.path.join(tmp_dir, name)
    with open(path, "w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return path


class KeywordIndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.log = _write_log(FIXTURE_EVENTS, self.tmp)

    def test_missing_log_returns_empty_index(self):
        index = build(os.path.join(self.tmp, "does_not_exist.jsonl"))
        self.assertEqual(index, {})

    def test_empty_log_returns_empty_index(self):
        empty = _write_log([], self.tmp, name="empty.jsonl")
        self.assertEqual(build(empty), {})

    def test_term_lookup_single(self):
        index = build(self.log)
        self.assertEqual(search(index, "alpha"), ["e1"])

    def test_term_lookup_shared_across_events(self):
        index = build(self.log)
        # 'gamma' appears in all three events.
        self.assertEqual(search(index, "gamma"), ["e1", "e2", "e3"])

    def test_case_insensitive_tokens(self):
        index = build(self.log)
        # Payload 'EPSILON' is upper; lookup must be lower, case-insensitive.
        self.assertEqual(search(index, "EPSILON"), ["e3"])
        self.assertEqual(search(index, "Epsilon"), ["e3"])
        self.assertEqual(search(index, "epsilon"), ["e3"])

    def test_multiple_docs_per_term(self):
        index = build(self.log)
        # 'beta' appears in e1 ('Alpha beta gamma') and e2 ('Beta gamma delta').
        self.assertEqual(search(index, "beta"), ["e1", "e2"])

    def test_unknown_term_returns_empty(self):
        index = build(self.log)
        self.assertEqual(search(index, "nonexistent"), [])

    def test_determinism(self):
        index_a = build(self.log)
        index_b = build(self.log)
        self.assertEqual(index_a, index_b)
        # Ordering of terms must be stable across builds.
        self.assertEqual(list(index_a.keys()), list(index_b.keys()))

    def test_immutability_of_returned_lists(self):
        index = build(self.log)
        result = search(index, "gamma")
        result.append("injected")
        # Mutating the returned list must not change the index.
        self.assertEqual(search(index, "gamma"), ["e1", "e2", "e3"])

    def test_immutability_of_returned_index(self):
        index = build(self.log)
        index["newterm"] = ["x"]
        # Mutating the returned index must not persist into a fresh build.
        fresh = build(self.log)
        self.assertNotIn("newterm", fresh)

    def test_read_only_no_log_mutation(self):
        before = os.path.getsize(self.log)
        build(self.log)
        # Rebuilding the index must not write to or truncate the log.
        self.assertEqual(os.path.getsize(self.log), before)
        with open(self.log, "r", encoding="utf-8") as handle:
            lines = [ln for ln in handle.read().splitlines() if ln.strip()]
        self.assertEqual(len(lines), len(FIXTURE_EVENTS))

    def test_skips_blank_and_unparseable_lines(self):
        messy = os.path.join(self.tmp, "messy.jsonl")
        with open(messy, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(FIXTURE_EVENTS[0], ensure_ascii=False) + "\n")
            handle.write("\n")  # blank line
            handle.write("{ this is not json }\n")  # broken line
            handle.write(json.dumps(FIXTURE_EVENTS[1], ensure_ascii=False) + "\n")
        index = build(messy)
        self.assertEqual(search(index, "alpha"), ["e1"])
        # 'beta' appears in e1 ('Alpha beta gamma') and e2 ('Beta gamma delta').
        self.assertEqual(search(index, "beta"), ["e1", "e2"])


if __name__ == "__main__":
    unittest.main()

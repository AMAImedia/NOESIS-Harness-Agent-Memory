import os
import tempfile
import unittest

from noesis_harness.observation_log import (
    LOG_PREFIX,
    TIMELINE_HEADING,
    ObservationLog,
    content_key,
)


class ObservationLogTests(unittest.TestCase):
    def log(self):
        return ObservationLog(tempfile.mkdtemp())

    def test_first_record_creates_artifact_with_frequency_one(self):
        log = self.log()
        summary = log.record("Loud Intro", "viewer", "intro too loud", "2026-01-02")
        self.assertTrue(summary["created"])
        self.assertEqual(summary["frequency"], 1)
        self.assertEqual(summary["timeline_entries"], 1)
        self.assertTrue(os.path.exists(summary["path"]))
        self.assertEqual(log.frequency("Loud Intro"), 1)

    def test_repeat_identical_note_increments_frequency_and_does_not_duplicate(self):
        log = self.log()
        first = log.record("k", "src", "same note", "2026-01-01")
        second = log.record("k", "src", "same note", "2026-01-02")
        self.assertFalse(second["created"])
        self.assertEqual(second["path"], first["path"])
        self.assertEqual(log.frequency("k"), 2)
        self.assertEqual(len(log.timeline("k")), 2)
        self.assertEqual(log.artifacts(), ["k"])

    def test_different_note_appends_new_timeline_entry(self):
        log = self.log()
        log.record("k", "src-a", "first statement", "2026-01-01")
        log.record("k", "src-b", "second statement", "2026-01-02")
        lines = log.timeline("k")
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].endswith("first statement"))
        self.assertTrue(lines[1].endswith("second statement"))
        self.assertEqual(log.frequency("k"), 2)

    def test_timeline_order_is_append_order(self):
        log = self.log()
        for day in ("2026-01-01", "2026-01-02", "2026-01-03"):
            log.record("k", "src", "note %s" % day, day)
        lines = log.timeline("k")
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("2026-01-01"))
        self.assertTrue(lines[1].startswith("2026-01-02"))
        self.assertTrue(lines[2].startswith("2026-01-03"))

    def test_timeline_line_format_uses_dated_source_note(self):
        log = self.log()
        log.record("k", "viewer", "too loud", "2026-01-02")
        self.assertEqual(log.timeline("k")[0], "2026-01-02 | viewer \u2014 too loud")

    def test_frequency_counter_accumulates_per_content_key(self):
        log = self.log()
        log.record("a", "s", "n", "2026-01-01")
        log.record("a", "s", "n", "2026-01-01")
        log.record("a", "s", "n", "2026-01-01")
        log.record("b", "s", "n", "2026-01-01")
        self.assertEqual(log.frequency("a"), 3)
        self.assertEqual(log.frequency("b"), 1)
        self.assertEqual(log.frequency("missing"), 0)

    def test_append_log_grammar_two_lines_without_refs(self):
        log = self.log()
        entry = log.append_log("2026-01-02", "Shipped log", "added observation store")
        lines = entry.split("\n")
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("## 20"))
        self.assertEqual(lines[0], "## 2026-01-02 \u00b7 Shipped log")
        self.assertEqual(lines[1], "What: added observation store")

    def test_append_log_grammar_three_lines_with_refs(self):
        log = self.log()
        entry = log.append_log(
            "2026-01-03", "Shipped log", "added store", "docs/LOG.md (new)"
        )
        lines = entry.split("\n")
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines[2], "Refs: docs/LOG.md (new)")
        self.assertTrue(lines[0].startswith(LOG_PREFIX))

    def test_append_log_is_append_only_newest_at_bottom(self):
        log = self.log()
        log.append_log("2026-01-01", "First", "one")
        log.append_log("2026-01-02", "Second", "two")
        entries = log.index_entries()
        self.assertEqual([entry["title"] for entry in entries], ["First", "Second"])

    def test_index_entries_parses_appended_entries(self):
        log = self.log()
        log.append_log("2026-01-01", "First", "what one", "refs one")
        log.append_log("2026-01-02", "Second", "what two")
        entries = log.index_entries()
        self.assertEqual(len(entries), 2)
        self.assertEqual(
            entries[0],
            {
                "date": "2026-01-01",
                "title": "First",
                "what": "what one",
                "refs": "refs one",
            },
        )
        self.assertEqual(entries[1]["date"], "2026-01-02")
        self.assertEqual(entries[1]["what"], "what two")
        self.assertEqual(entries[1]["refs"], "")

    def test_index_entries_skips_malformed_blocks(self):
        log = self.log()
        os.makedirs(log.root, exist_ok=True)
        with open(
            os.path.join(log.root, "LOG.md"), "w", encoding="utf-8", newline="\n"
        ) as handle:
            handle.write("random prose with no header\n")
            handle.write("## not-a-date \u00b7 bogus\n")
            handle.write("What: dangling\n")
        log.append_log("2026-01-05", "Valid", "good entry")
        entries = log.index_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["title"], "Valid")
        self.assertEqual(entries[0]["date"], "2026-01-05")

    def test_artifact_path_sanitizes_key(self):
        log = self.log()
        path = log.artifact_path("Hello, World!! 2026")
        self.assertTrue(path.endswith("hello-world-2026.md"))
        self.assertEqual(os.path.dirname(path), log.root)

    def test_artifact_path_rejects_unsafe_keys(self):
        log = self.log()
        for bad in ("..", "../etc/passwd", "a/b", "a\\b", "", "   "):
            with self.assertRaises(ValueError):
                log.artifact_path(bad)

    def test_determinism_identical_sequences_produce_identical_bytes(self):
        def run(root):
            log = ObservationLog(root)
            log.record("Alpha", "src-b", "note two", "2026-01-02")
            log.record("Alpha", "src-a", "note one", "2026-01-01")
            log.record("Beta", "src-a", "note one", "2026-01-01")
            log.append_log("2026-01-02", "Ship", "did the thing", "ref")
            paths = [log.artifact_path("Alpha"), log.artifact_path("Beta")]
            paths.append(os.path.join(log.root, "LOG.md"))
            return paths

        left_root = tempfile.mkdtemp()
        right_root = tempfile.mkdtemp()
        left_paths = run(left_root)
        right_paths = run(right_root)
        for left, right in zip(left_paths, right_paths):
            with open(left, "rb") as handle:
                left_bytes = handle.read()
            with open(right, "rb") as handle:
                right_bytes = handle.read()
            self.assertEqual(left_bytes, right_bytes)

    def test_content_key_is_stable_and_content_addressed(self):
        first = content_key("src", "note")
        self.assertEqual(first, content_key("src", "note"))
        self.assertEqual(len(first), 64)
        self.assertNotEqual(first, content_key("src", "other note"))
        self.assertNotEqual(first, content_key("other src", "note"))

    def test_artifacts_returns_sorted_keys(self):
        log = self.log()
        for key in ("Zulu", "alpha", "Mike"):
            log.record(key, "src", "note", "2026-01-01")
        self.assertEqual(log.artifacts(), ["alpha", "mike", "zulu"])

    def test_frontmatter_contains_kind_and_frequency(self):
        log = self.log()
        log.record("k", "src", "note", "2026-01-01")
        log.record("k", "src", "note", "2026-01-02")
        with open(log.artifact_path("k"), "r", encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("kind: artifact", text)
        self.assertIn("frequency: 2", text)
        self.assertIn("sources: [\"src\"]", text)
        self.assertIn(TIMELINE_HEADING, text)
        body = text.split(TIMELINE_HEADING)[0]
        self.assertIn("note", body)


if __name__ == "__main__":
    unittest.main()

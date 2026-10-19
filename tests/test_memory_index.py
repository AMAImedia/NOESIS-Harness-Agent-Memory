"""tests/test_memory_index.py

Unit tests for noesis_harness.memory_index.

Stdlib only. Run: python -m unittest tests.test_memory_index -q
"""

import os
import unittest

from noesis_harness.memory_index import (
    ENTRY_MAX_CHARS,
    MAX_ENTRYPOINT_BYTES,
    MAX_ENTRYPOINT_LINES,
    MemoryIndex,
    MemoryRecord,
    MemoryRecordError,
    MemoryType,
    parse_record,
    render_record,
    safe_memory_path,
)


class TestMemoryRecord(unittest.TestCase):
    def test_render_parse_roundtrip(self):
        record = MemoryRecord(
            name="build-cmd",
            description="How to build the project",
            type=MemoryType.PROJECT,
            body="Run `make build`.",
        )
        parsed = parse_record(render_record(record))
        self.assertEqual(parsed.name, record.name)
        self.assertEqual(parsed.description, record.description)
        self.assertEqual(parsed.type, MemoryType.PROJECT)
        self.assertEqual(parsed.body, record.body)

    def test_render_parse_missing_body_is_tolerated(self):
        record = MemoryRecord("empty", "no body here", MemoryType.USER)
        parsed = parse_record(render_record(record))
        self.assertEqual(parsed.body, "")

    def test_type_coercion_from_string(self):
        record = MemoryRecord("n", "d", "feedback")
        self.assertIs(record.type, MemoryType.FEEDBACK)

    def test_unknown_type_raises(self):
        with self.assertRaises(MemoryRecordError):
            MemoryRecord("n", "d", "bogus")

    def test_empty_name_raises(self):
        with self.assertRaises(MemoryRecordError):
            MemoryRecord("   ", "d", MemoryType.USER)

    def test_empty_description_raises(self):
        with self.assertRaises(MemoryRecordError):
            MemoryRecord("n", "", MemoryType.USER)

    def test_quoting_of_description_containing_colon(self):
        record = MemoryRecord("n", "priority: high", MemoryType.REFERENCE)
        text = render_record(record)
        self.assertIn('description: "priority: high"', text)
        self.assertEqual(parse_record(text).description, "priority: high")

    def test_embedded_quote_escaping(self):
        record = MemoryRecord("n", 'say "hi"', MemoryType.USER)
        text = render_record(record)
        self.assertIn('description: "say ""hi"""', text)
        self.assertEqual(parse_record(text).description, 'say "hi"')

    def test_missing_frontmatter_raises(self):
        with self.assertRaises(MemoryRecordError):
            parse_record("just some text\nwithout delimiters")

    def test_missing_required_field_raises(self):
        with self.assertRaises(MemoryRecordError):
            parse_record("---\nname: x\ntype: user\n---\n\nbody")


class TestMemoryIndex(unittest.TestCase):
    def _sample(self):
        index = MemoryIndex()
        index.add(MemoryRecord("alpha", "first", MemoryType.USER))
        index.add(MemoryRecord("beta", "second", MemoryType.PROJECT))
        index.add(MemoryRecord("gamma", "third", MemoryType.USER))
        return index

    def test_add_dedupes_by_name(self):
        index = self._sample()
        index.add(MemoryRecord("alpha", "replaced", MemoryType.REFERENCE))
        names = [r.name for r in index.entries()]
        self.assertEqual(names.count("alpha"), 1)
        alpha = [r for r in index.entries() if r.name == "alpha"][0]
        self.assertEqual(alpha.description, "replaced")

    def test_entries_sorted_by_type_then_name(self):
        index = self._sample()
        got = [(r.type.value, r.name) for r in index.entries()]
        self.assertEqual(
            got,
            [("project", "beta"), ("user", "alpha"), ("user", "gamma")],
        )

    def test_types_counts(self):
        index = self._sample()
        self.assertEqual(index.types(), {"project": 1, "user": 2})

    def test_find_case_insensitive(self):
        index = MemoryIndex()
        index.add(MemoryRecord("Alpha", "First Thing", MemoryType.USER, body="Note"))
        index.add(MemoryRecord("beta", "second", MemoryType.PROJECT))
        self.assertEqual([r.name for r in index.find("FIRST")], ["Alpha"])
        self.assertEqual([r.name for r in index.find("note")], ["Alpha"])
        self.assertEqual([r.name for r in index.find("zzz")], [])

    def test_rebuild_line_cap(self):
        index = MemoryIndex()
        for i in range(10):
            index.add(MemoryRecord("r%02d" % i, "desc", MemoryType.USER))
        text = index.rebuild(max_lines=4, max_bytes=MAX_ENTRYPOINT_BYTES)
        lines = text.split("\n")
        self.assertEqual(len(lines), 4)
        self.assertTrue(lines[-1].startswith("# truncated: "))
        self.assertIn("7 entries omitted", lines[-1])

    def test_rebuild_byte_cap_multibyte_stays_within_cap(self):
        index = MemoryIndex()
        for i in range(50):
            index.add(
                MemoryRecord("name%02d" % i, "\u044f" * 40, MemoryType.PROJECT)
            )
        cap = 400
        text = index.rebuild(max_lines=MAX_ENTRYPOINT_LINES, max_bytes=cap)
        self.assertLessEqual(len(text.encode("utf-8")), cap)
        self.assertIn("# truncated: ", text)

    def test_rebuild_truncation_warning_when_over_cap(self):
        index = MemoryIndex()
        for i in range(5):
            index.add(MemoryRecord("r%d" % i, "d", MemoryType.REFERENCE))
        text = index.rebuild(max_lines=3, max_bytes=MAX_ENTRYPOINT_BYTES)
        self.assertIn("# truncated: 3 entries omitted", text)

    def test_rebuild_no_warning_when_within_caps(self):
        index = self._sample()
        text = index.rebuild()
        self.assertNotIn("truncated", text)
        self.assertEqual(len(text.split("\n")), 3)

    def test_entry_truncated_to_max_chars(self):
        index = MemoryIndex()
        index.add(MemoryRecord("n", "x" * 500, MemoryType.USER))
        text = index.rebuild()
        line = text.split("\n")[0]
        self.assertLessEqual(len(line), ENTRY_MAX_CHARS)


class TestSafeMemoryPath(unittest.TestCase):
    def test_accepts_normal_name(self):
        base = "root"
        self.assertEqual(
            safe_memory_path(base, "notes.md"),
            os.path.join("root", "notes.md"),
        )

    def test_rejects_traversal(self):
        with self.assertRaises(MemoryRecordError):
            safe_memory_path("root", "../escape.md")

    def test_rejects_absolute(self):
        with self.assertRaises(MemoryRecordError):
            safe_memory_path("root", "/etc/passwd")

    def test_rejects_drive_letter(self):
        with self.assertRaises(MemoryRecordError):
            safe_memory_path("root", "C:\\evil.md")

    def test_rejects_unc(self):
        with self.assertRaises(MemoryRecordError):
            safe_memory_path("root", "\\\\server\\share\\evil.md")

    def test_rejects_null_byte(self):
        with self.assertRaises(MemoryRecordError):
            safe_memory_path("root", "bad\x00name.md")


if __name__ == "__main__":
    unittest.main()

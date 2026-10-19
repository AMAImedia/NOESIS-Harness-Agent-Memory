"""Tests for noesis_harness.tool_dialect.

Verifies that the per-harness tool dialect table is data-driven, that lookups
are case-insensitive and fail soft to the default dialect, and that argument
normalization/denormalization round-trips deterministically without mutating
caller input.
"""

import unittest

from noesis_harness import tool_dialect
from noesis_harness.tool_dialect import (
    CANONICAL_KEYS,
    DEFAULT_DIALECT_NAME,
    DIALECTS,
    ToolDialect,
    denormalize_tool_args,
    dialect_for,
    dialects,
    normalize_tool_args,
    tool_name_for,
)


class TestDialectLookup(unittest.TestCase):

    def test_dialect_for_known(self):
        self.assertEqual(dialect_for("claude").path_key, "file_path")
        self.assertEqual(dialect_for("cursor").shell_tool, "Shell")
        self.assertEqual(dialect_for("copilot").old_string_key, "old_str")

    def test_dialect_for_unknown_fallback(self):
        self.assertIs(dialect_for("nope"), DIALECTS[DEFAULT_DIALECT_NAME])
        self.assertIs(dialect_for(""), DIALECTS[DEFAULT_DIALECT_NAME])

    def test_dialect_for_case_insensitive(self):
        self.assertIs(dialect_for("CLAUDE"), DIALECTS["claude"])
        self.assertIs(dialect_for("Cursor"), DIALECTS["cursor"])
        self.assertIs(dialect_for("QWEN"), DIALECTS["qwen"])

    def test_dialect_default_name_present(self):
        self.assertIn(DEFAULT_DIALECT_NAME, DIALECTS)

    def test_dialects_sorted(self):
        names = dialects()
        self.assertEqual(names, sorted(names))
        self.assertEqual(len(names), len(DIALECTS))
        self.assertEqual(names, sorted(DIALECTS.keys()))

    def test_each_dialect_fields_non_empty(self):
        for key, dialect in DIALECTS.items():
            self.assertIsInstance(dialect, ToolDialect)
            self.assertEqual(dialect.name, key)
            self.assertTrue(dialect.path_key)
            self.assertTrue(dialect.shell_tool)
            self.assertTrue(dialect.old_string_key)
            self.assertTrue(dialect.command_key)


class TestNormalize(unittest.TestCase):

    def test_normalize_maps_all_three_keys(self):
        raw = {"file_path": "/a", "old_string": "x", "command": "ls"}
        self.assertEqual(
            normalize_tool_args("claude", raw),
            {"path": "/a", "old_string": "x", "command": "ls"},
        )

    def test_normalize_preserves_unknown_keys(self):
        raw = {"file_path": "/a", "timeout": 5}
        self.assertEqual(
            normalize_tool_args("claude", raw),
            {"path": "/a", "timeout": 5},
        )

    def test_normalize_does_not_mutate_input(self):
        raw = {"file_path": "/a", "old_str": "x", "command": "ls"}
        snapshot = dict(raw)
        normalize_tool_args("cursor", raw)
        self.assertEqual(raw, snapshot)

    def test_normalize_canonical_key_order(self):
        raw = {"zzz": 1, "command": "ls", "file_path": "/a", "aaa": 2,
               "old_string": "x"}
        out = normalize_tool_args("claude", raw)
        self.assertEqual(
            list(out.keys()),
            ["path", "old_string", "command", "aaa", "zzz"],
        )

    def test_canonical_keys_constant(self):
        self.assertEqual(CANONICAL_KEYS, ("path", "old_string", "command"))

    def test_qwen_and_codex_differences(self):
        qwen_raw = {"file_path": "/a", "old_string": "x", "command": "ls"}
        codex_raw = {"path": "/a", "old_string": "x", "cmd": "ls"}
        qwen = normalize_tool_args("qwen", qwen_raw)
        codex = normalize_tool_args("codex", codex_raw)
        expected = {"path": "/a", "old_string": "x", "command": "ls"}
        self.assertEqual(qwen, expected)
        self.assertEqual(codex, expected)
        self.assertEqual(
            denormalize_tool_args("qwen", qwen),
            {"file_path": "/a", "old_string": "x", "command": "ls"},
        )
        self.assertEqual(
            denormalize_tool_args("codex", codex),
            {"path": "/a", "old_string": "x", "cmd": "ls"},
        )
        self.assertNotEqual(
            denormalize_tool_args("qwen", qwen),
            denormalize_tool_args("codex", codex),
        )


class TestDenormalize(unittest.TestCase):

    def test_denormalize_inverse_roundtrip(self):
        for harness in dialects():
            canonical = {"path": "/a", "old_string": "x", "command": "ls"}
            raw = denormalize_tool_args(harness, canonical)
            self.assertEqual(normalize_tool_args(harness, raw), canonical)

    def test_denormalize_preserves_other_keys(self):
        out = denormalize_tool_args("cursor", {"path": "/a", "extra": True})
        self.assertEqual(out, {"path": "/a", "extra": True})

    def test_denormalize_does_not_mutate_input(self):
        canonical = {"path": "/a", "command": "ls"}
        snapshot = dict(canonical)
        denormalize_tool_args("codex", canonical)
        self.assertEqual(canonical, snapshot)


class TestToolName(unittest.TestCase):

    def test_tool_name_for_shell_per_dialect(self):
        self.assertEqual(tool_name_for("claude", "shell"), "Bash")
        self.assertEqual(tool_name_for("cursor", "shell"), "Shell")
        self.assertEqual(tool_name_for("copilot", "shell"), "shell")
        self.assertEqual(tool_name_for("codex", "shell"), "shell")
        self.assertEqual(tool_name_for("qwen", "shell"), "Bash")

    def test_tool_name_for_other_unchanged(self):
        self.assertEqual(tool_name_for("claude", "grep"), "grep")
        self.assertEqual(tool_name_for("unknown", "read_file"), "read_file")


if __name__ == "__main__":
    unittest.main()

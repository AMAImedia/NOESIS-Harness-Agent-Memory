"""Tests for noesis_harness.shared_board."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from noesis_harness.shared_board import (
    Confidence,
    SharedBoard,
    TaskNotification,
    WriteConflict,
    safe_name,
)


class TestSafeName(unittest.TestCase):

    def test_plain_name_unchanged(self):
        self.assertEqual(safe_name("board-01_a.txt"), "board-01_a.txt")

    def test_rejects_parent_traversal(self):
        for name in ("..", "../etc/passwd", "a/../../b", "..\\win"):
            with self.assertRaises(ValueError):
                safe_name(name)

    def test_rejects_separators(self):
        for name in ("a/b", "a\\b"):
            with self.assertRaises(ValueError):
                safe_name(name)

    def test_rejects_empty_and_nul(self):
        with self.assertRaises(ValueError):
            safe_name("")
        with self.assertRaises(ValueError):
            safe_name("a\x00b")

    def test_replaces_unsafe_characters(self):
        self.assertEqual(safe_name("a b:c*d"), "a_b_c_d")

    def test_rejects_non_str(self):
        with self.assertRaises(TypeError):
            safe_name(123)  # type: ignore[arg-type]


class TestTaskNotification(unittest.TestCase):

    def test_confidence_values(self):
        self.assertEqual(Confidence.HIGH.value, "HIGH")
        self.assertEqual(Confidence.MEDIUM.value, "MEDIUM")
        self.assertEqual(Confidence.LOW.value, "LOW")

    def test_default_confidence_is_medium(self):
        note = TaskNotification(task_id="t1", status="ok", summary="s")
        self.assertEqual(note.confidence, Confidence.MEDIUM)
        self.assertEqual(note.result, "")
        self.assertEqual(note.usage, {})

    def test_envelope_header_and_children(self):
        note = TaskNotification(
            task_id="t1",
            status="done",
            summary="did the thing",
            result="42",
            usage={"tokens": 10},
            confidence=Confidence.HIGH,
        )
        text = note.to_text()
        self.assertIn(
            '<task-note task-id="t1" status="done" confidence="HIGH">',
            text,
        )
        self.assertIn("<summary>did the thing</summary>", text)
        self.assertIn("<result>42</result>", text)
        self.assertIn("<usage>", text)

    def test_text_roundtrip(self):
        note = TaskNotification(
            task_id="task-9",
            status="partial",
            summary="half done",
            result="rows=3",
            usage={"tokens": 128, "cost": 0.02},
            confidence=Confidence.LOW,
        )
        restored = TaskNotification.from_text(note.to_text())
        self.assertEqual(restored, note)

    def test_text_escaping_roundtrip(self):
        note = TaskNotification(
            task_id="t<2>",
            status="a&b",
            summary="5 < 6 & 7 > 6",
            result="<xml> & more",
            confidence=Confidence.HIGH,
        )
        text = note.to_text()
        self.assertIn("&lt;", text)
        self.assertIn("&amp;", text)
        restored = TaskNotification.from_text(text)
        self.assertEqual(restored.summary, "5 < 6 & 7 > 6")
        self.assertEqual(restored.result, "<xml> & more")
        self.assertEqual(restored.task_id, "t<2>")
        self.assertEqual(restored.status, "a&b")

    def test_usage_canonical_json(self):
        note = TaskNotification(
            task_id="t",
            status="ok",
            summary="s",
            usage={"b": 1, "a": 2},
        )
        text = note.to_text()
        self.assertIn('<usage>{"a":2,"b":1}</usage>', text)

    def test_from_text_missing_task_id_raises(self):
        with self.assertRaises(ValueError):
            TaskNotification.from_text(
                '<task-note status="ok"></task-note>'
            )

    def test_from_text_missing_status_raises(self):
        with self.assertRaises(ValueError):
            TaskNotification.from_text(
                '<task-note task-id="t"></task-note>'
            )

    def test_from_text_unknown_confidence_falls_back(self):
        note = TaskNotification.from_text(
            '<task-note task-id="t" status="ok" confidence="MAYBE">'
            "<summary>s</summary></task-note>"
        )
        self.assertEqual(note.confidence, Confidence.MEDIUM)

    def test_from_text_tolerates_missing_children(self):
        note = TaskNotification.from_text(
            '<task-note task-id="t" status="ok"></task-note>'
        )
        self.assertEqual(note.summary, "")
        self.assertEqual(note.result, "")
        self.assertEqual(note.usage, {})


class TestSharedBoard(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name
        self.board = SharedBoard(self.root)

    def test_publish_then_read(self):
        self.board.publish("tasks", {"id": 1, "v": "a"})
        self.board.publish("tasks", {"id": 2, "v": "b"})
        records = self.board.read("tasks")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["id"], 1)
        self.assertEqual(records[1]["id"], 2)

    def test_publish_returns_topic_path(self):
        path = self.board.publish("tasks", {"id": 1})
        self.assertEqual(path, os.path.join(self.root, "tasks.jsonl"))
        self.assertTrue(os.path.isfile(path))

    def test_publish_duplicate_is_idempotent(self):
        self.board.publish("tasks", {"id": 1, "v": "a"})
        self.board.publish("tasks", {"v": "a", "id": 1})
        self.assertEqual(len(self.board.read("tasks")), 1)

    def test_read_limit_returns_prefix_in_order(self):
        for index in range(5):
            self.board.publish("tasks", {"id": index})
        limited = self.board.read("tasks", limit=2)
        self.assertEqual([item["id"] for item in limited], [0, 1])
        self.assertEqual(len(self.board.read("tasks", limit=0)), 5)

    def test_read_missing_topic_is_empty(self):
        self.assertEqual(self.board.read("never"), [])

    def test_publish_rejects_non_dict(self):
        with self.assertRaises(TypeError):
            self.board.publish("tasks", ["not", "a", "dict"])  # type: ignore[arg-type]

    def test_write_and_read_file_roundtrip(self):
        path = self.board.write_file("alpha", "hello board")
        self.assertEqual(path, os.path.join(self.root, "alpha"))
        self.assertEqual(self.board.read_file("alpha"), "hello board")

    def test_read_missing_file_returns_none(self):
        self.assertIsNone(self.board.read_file("absent"))

    def test_write_file_same_content_no_rewrite(self):
        self.board.write_file("alpha", "stable")
        before = os.stat(os.path.join(self.root, "alpha"))
        self.board.write_file("alpha", "stable")
        after = os.stat(os.path.join(self.root, "alpha"))
        self.assertEqual(before.st_mtime_ns, after.st_mtime_ns)
        self.assertEqual(before.st_ino, after.st_ino)

    def test_write_file_new_content_replaces_content(self):
        self.board.write_file("alpha", "one")
        self.board.write_file("alpha", "two")
        self.assertEqual(self.board.read_file("alpha"), "two")

    def test_files_sorted(self):
        for name in ("zeta", "alpha", "mid"):
            self.board.write_file(name, name)
        self.assertEqual(self.board.files(), ["alpha", "mid", "zeta"])

    def test_files_excludes_topics(self):
        self.board.write_file("alpha", "a")
        self.board.publish("tasks", {"id": 1})
        self.assertEqual(self.board.files(), ["alpha"])

    def test_notify_and_notifications_roundtrip(self):
        note = TaskNotification(
            task_id="t-1",
            status="done",
            summary="compiled",
            result="ok",
            usage={"tokens": 7},
            confidence=Confidence.HIGH,
        )
        self.board.notify("inbox", note)
        restored = self.board.notifications("inbox")
        self.assertEqual(restored, [note])

    def test_notify_dedupes_identical_notification(self):
        note = TaskNotification(task_id="t-1", status="done", summary="x")
        self.board.notify("inbox", note)
        self.board.notify("inbox", note)
        self.assertEqual(len(self.board.notifications("inbox")), 1)

    def test_notifications_skips_bad_records(self):
        self.board.publish("inbox", {"unrelated": True})
        self.board.notify(
            "inbox", TaskNotification(task_id="t", status="ok", summary="s")
        )
        self.assertEqual(len(self.board.notifications("inbox")), 1)

    def test_board_never_deletes_existing_files(self):
        self.board.write_file("keep", "keep me")
        self.board.publish("tasks", {"id": 1})
        self.board.publish("tasks", {"id": 2})
        self.board.write_file("also", "and me")
        self.assertTrue(os.path.isfile(os.path.join(self.root, "keep")))
        self.assertEqual(self.board.read_file("keep"), "keep me")
        self.assertEqual(len(self.board.read("tasks")), 2)

    def test_lazy_root_creation(self):
        nested = os.path.join(self.root, "deep", "board")
        board = SharedBoard(nested)
        self.assertFalse(os.path.isdir(nested))
        board.publish("tasks", {"id": 1})
        self.assertTrue(os.path.isdir(nested))

    def test_determinism_across_instances(self):
        def populate(root):
            board = SharedBoard(root)
            board.write_file("alpha", "same")
            board.publish("tasks", {"b": 2, "a": 1})
            board.notify(
                "inbox",
                TaskNotification(
                    task_id="t",
                    status="ok",
                    summary="s",
                    usage={"z": 1, "y": 2},
                    confidence=Confidence.LOW,
                ),
            )

        other_root = os.path.join(self.root, "other")
        populate(self.root)
        populate(other_root)

        self.assertEqual(
            self.board.read_file("alpha"), SharedBoard(other_root).read_file("alpha")
        )
        self.assertEqual(self.board.read("tasks"), SharedBoard(other_root).read("tasks"))
        self.assertEqual(
            self.board.notifications("inbox"),
            SharedBoard(other_root).notifications("inbox"),
        )

    def test_stored_topic_is_valid_jsonl(self):
        self.board.publish("tasks", {"id": 1})
        self.board.publish("tasks", {"id": 2})
        with open(os.path.join(self.root, "tasks.jsonl"), "r", encoding="utf-8") as fh:
            lines = [line for line in fh.read().splitlines() if line]
        self.assertEqual(len(lines), 2)
        for line in lines:
            json.loads(line)

    def test_write_conflict_is_runtime_error(self):
        self.assertTrue(issubclass(WriteConflict, RuntimeError))

    def test_write_file_rejects_non_str(self):
        with self.assertRaises(TypeError):
            self.board.write_file("alpha", b"bytes")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()

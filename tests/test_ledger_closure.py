"""Tests for noesis_harness.ledger_closure.

Pins the append-only causal ledger contract: every committed intent must be
paired with a terminal event, and interrupted or aborted intents are closed
with a synthetic terminal record rather than left dangling.
"""

import json
import tempfile
import unittest
from pathlib import Path

from noesis_harness.ledger_closure import LedgerClosure, LedgerError, closure_summary


class LedgerClosureTests(unittest.TestCase):
    def _ledger(self, root):
        return LedgerClosure(str(Path(root) / "ledger.jsonl"))

    def test_open_then_pending_contains_intent(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self._ledger(root)
            event_id = ledger.open_intent("i-1", "translate", {"slot": 3})
            self.assertEqual(event_id, "open:i-1")
            self.assertEqual(ledger.pending(), ["i-1"])
            self.assertFalse(ledger.is_closed("i-1"))

    def test_close_removes_from_pending(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self._ledger(root)
            ledger.open_intent("i-1", "translate")
            ledger.open_intent("i-2", "translate")
            self.assertEqual(ledger.pending(), ["i-1", "i-2"])
            ledger.close_intent("i-1", "completed")
            self.assertEqual(ledger.pending(), ["i-2"])
            self.assertTrue(ledger.is_closed("i-1"))

    def test_double_open_raises(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self._ledger(root)
            ledger.open_intent("i-1", "translate")
            with self.assertRaises(LedgerError):
                ledger.open_intent("i-1", "translate")

    def test_open_after_close_raises(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self._ledger(root)
            ledger.open_intent("i-1", "translate")
            ledger.close_intent("i-1", "completed")
            with self.assertRaises(LedgerError):
                ledger.open_intent("i-1", "translate")

    def test_close_without_open_raises(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self._ledger(root)
            with self.assertRaises(LedgerError):
                ledger.close_intent("ghost", "completed")

    def test_double_close_same_outcome_is_idempotent(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self._ledger(root)
            ledger.open_intent("i-1", "translate")
            first = ledger.close_intent("i-1", "completed")
            second = ledger.close_intent("i-1", "completed")
            self.assertEqual(first, "close:i-1")
            self.assertEqual(second, first)
            self.assertEqual(ledger.count(), 2)

    def test_double_close_different_outcome_raises(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self._ledger(root)
            ledger.open_intent("i-1", "translate")
            ledger.close_intent("i-1", "completed")
            with self.assertRaises(LedgerError):
                ledger.close_intent("i-1", "aborted")

    def test_close_all_pending_marks_synthetic(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self._ledger(root)
            ledger.open_intent("b", "clone")
            ledger.open_intent("a", "clone")
            ledger.open_intent("c", "clone")
            ledger.close_intent("c", "completed")
            closed = ledger.close_all_pending("aborted")
            self.assertEqual(closed, ["a", "b"])
            self.assertEqual(ledger.pending(), [])
            projection = ledger.state()
            self.assertTrue(projection["a"]["synthetic"])
            self.assertTrue(projection["b"]["synthetic"])
            self.assertFalse(projection["c"]["synthetic"])

    def test_state_projection_fields(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self._ledger(root)
            ledger.open_intent("i-1", "translate", {"slot": 1})
            ledger.open_intent("i-2", "clone")
            ledger.close_intent("i-1", "completed")
            projection = ledger.state()
            self.assertEqual(sorted(projection.keys()), ["i-1", "i-2"])
            self.assertEqual(
                projection["i-1"],
                {"kind": "translate", "outcome": "completed",
                 "synthetic": False, "closed": True},
            )
            self.assertEqual(
                projection["i-2"],
                {"kind": "clone", "outcome": None,
                 "synthetic": False, "closed": False},
            )

    def test_replay_determinism_digest_equal(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / "ledger.jsonl")
            ledger = LedgerClosure(path)
            ledger.open_intent("i-1", "translate")
            ledger.open_intent("i-2", "clone")
            ledger.close_intent("i-1", "completed")
            ledger.close_all_pending("aborted")
            reopened = LedgerClosure(path)
            self.assertEqual(ledger.digest(), reopened.digest())
            self.assertEqual(ledger.state(), reopened.state())
            self.assertEqual(reopened.pending(), [])

    def test_malformed_tail_repair(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "ledger.jsonl"
            ledger = LedgerClosure(str(path))
            ledger.open_intent("i-1", "translate")
            ledger.close_intent("i-1", "completed")
            expected = ledger.digest()
            with open(path, "ab") as fh:
                fh.write(b'{"event_id": "open:i-1"')
            repaired = LedgerClosure(str(path))
            self.assertEqual(repaired.digest(), expected)
            self.assertTrue(path.read_bytes().endswith(b"\n"))
            repaired.open_intent("i-2", "clone")
            self.assertEqual(repaired.pending(), ["i-2"])

    def test_earlier_corruption_raises(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "ledger.jsonl"
            ledger = LedgerClosure(str(path))
            ledger.open_intent("i-1", "translate")
            ledger.open_intent("i-2", "clone")
            raw = path.read_text(encoding="utf-8").splitlines(keepends=True)
            raw[0] = "not-json\n"
            path.write_text("".join(raw), encoding="utf-8")
            with self.assertRaises(LedgerError):
                LedgerClosure(str(path))

    def test_count_and_digest_stable(self):
        with tempfile.TemporaryDirectory() as root:
            path = str(Path(root) / "ledger.jsonl")
            ledger = LedgerClosure(path)
            self.assertEqual(ledger.count(), 0)
            ledger.open_intent("i-1", "translate")
            ledger.open_intent("i-2", "clone")
            self.assertEqual(ledger.count(), 2)
            ledger.close_intent("i-1", "completed")
            self.assertEqual(ledger.count(), 3)
            first = ledger.digest()
            self.assertEqual(first, ledger.digest())
            self.assertTrue(first.startswith("sha256:"))
            self.assertEqual(first, LedgerClosure(path).digest())

    def test_empty_ledger_summary(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self._ledger(root)
            summary = closure_summary(ledger)
            self.assertEqual(summary["opened"], 0)
            self.assertEqual(summary["closed"], 0)
            self.assertEqual(summary["pending"], 0)
            self.assertEqual(summary["synthetic_closed"], 0)
            self.assertEqual(summary["digest"], ledger.digest())

    def test_closure_summary_counts(self):
        with tempfile.TemporaryDirectory() as root:
            ledger = self._ledger(root)
            ledger.open_intent("i-1", "translate")
            ledger.open_intent("i-2", "clone")
            ledger.close_intent("i-1", "completed")
            ledger.close_all_pending("aborted")
            summary = closure_summary(ledger)
            self.assertEqual(summary["opened"], 2)
            self.assertEqual(summary["closed"], 2)
            self.assertEqual(summary["pending"], 0)
            self.assertEqual(summary["synthetic_closed"], 1)

    def test_file_records_have_event_shape(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "ledger.jsonl"
            ledger = LedgerClosure(str(path))
            ledger.open_intent("i-1", "translate")
            ledger.close_intent("i-1", "completed")
            records = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertEqual(len(records), 2)
            for record in records:
                self.assertEqual(
                    sorted(record.keys()),
                    ["event_id", "payload", "seq", "type"],
                )
            self.assertEqual(records[0]["type"], "intent_opened")
            self.assertEqual(records[1]["type"], "intent_closed")
            self.assertEqual(records[0]["event_id"], "open:i-1")
            self.assertEqual(records[1]["event_id"], "close:i-1")


if __name__ == "__main__":
    unittest.main()

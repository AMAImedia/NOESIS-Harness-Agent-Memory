import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from noesis_harness.turn_checkpoint import DurableTurnCheckpointStore, TurnCheckpointError


class TurnCheckpointTests(unittest.TestCase):
    def test_commit_every_turn_and_resume(self):
        with tempfile.TemporaryDirectory() as root:
            store = DurableTurnCheckpointStore(str(Path(root) / "turns.sqlite3"), clock=lambda: 10.0)
            first = store.begin("run-1")
            self.assertEqual(first.turn, -1)
            turn0 = store.commit_turn("run-1", 0, {"cursor": 1}, {"output": "a"})
            turn1 = store.commit_turn("run-1", 1, {"cursor": 2}, {"output": "b"}, done=True)
            self.assertEqual(turn1.status, "completed")
            self.assertTrue(store.verify_chain("run-1"))
            reopened = DurableTurnCheckpointStore(str(Path(root) / "turns.sqlite3"), clock=lambda: 20.0)
            restored = reopened.recover("run-1")
            self.assertEqual(restored.turn, 1)
            self.assertEqual(restored.status, "running")
            self.assertEqual(restored.state["cursor"], 2)

    def test_turns_cannot_skip_or_move_backwards(self):
        with tempfile.TemporaryDirectory() as root:
            store = DurableTurnCheckpointStore(str(Path(root) / "turns.sqlite3"))
            store.begin("run-2")
            with self.assertRaisesRegex(TurnCheckpointError, "turn_not_sequential"):
                store.commit_turn("run-2", 1, {}, {})
            store.commit_turn("run-2", 0, {}, {})
            with self.assertRaisesRegex(TurnCheckpointError, "turn_not_sequential"):
                store.commit_turn("run-2", 0, {}, {})

    def test_corrupted_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "turns.sqlite3"
            store = DurableTurnCheckpointStore(str(path))
            store.begin("run-3")
            store.commit_turn("run-3", 0, {"safe": True}, "output")
            db = sqlite3.connect(path)
            try:
                with db:
                    db.execute("UPDATE turn_checkpoints SET payload=? WHERE run_id=? AND turn=?", ("{\"corrupt\":true}", "run-3", 0))
            finally:
                db.close()
            with self.assertRaisesRegex(TurnCheckpointError, "checkpoint_corrupt"):
                store.latest("run-3")

    def test_interrupt_is_recoverable_without_erasing_last_state(self):
        with tempfile.TemporaryDirectory() as root:
            store = DurableTurnCheckpointStore(str(Path(root) / "turns.sqlite3"))
            store.begin("run-4")
            store.commit_turn("run-4", 0, {"cursor": "safe"}, "x")
            interrupted = store.interrupt("run-4", "kill_during_write")
            self.assertEqual(interrupted.status, "interrupted")
            resumed = store.recover("run-4")
            self.assertEqual(resumed.state["cursor"], "safe")
            self.assertEqual(resumed.status, "running")


if __name__ == "__main__":
    unittest.main()

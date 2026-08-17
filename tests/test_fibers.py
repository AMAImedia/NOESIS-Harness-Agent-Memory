import sqlite3
import tempfile
import unittest
from pathlib import Path

from noesis_harness.fibers import FiberCorrupt, FiberStore


class FiberTests(unittest.TestCase):
    def test_resume_after_interruption_uses_last_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            store = FiberStore(str(Path(d) / "fibers.db"))
            fid = store.register("research", {"topic": "x"})
            calls = []
            def flaky(step, state, payload):
                calls.append(step)
                if len(calls) == 1:
                    raise RuntimeError("injected crash")
                return {"step": step + 1, "state": {"answer": "ok"}, "done": True}
            with self.assertRaises(RuntimeError): store.resume(fid, flaky)
            self.assertEqual(store.get(fid).status, "interrupted")
            record = store.resume(fid, flaky)
            self.assertEqual(record.status, "completed")
            self.assertEqual(record.step, 1)
            self.assertEqual(calls, [0, 0])

    def test_checkpoint_is_monotonic_and_recoverable(self):
        with tempfile.TemporaryDirectory() as d:
            store = FiberStore(str(Path(d) / "fibers.db"))
            fid = store.register("long")
            store.checkpoint(fid, 3, {"items": [1, 2, 3]})
            with self.assertRaises(ValueError): store.checkpoint(fid, 2, {})
            self.assertIn(fid, [x.fiber_id for x in store.recoverable()])
            self.assertEqual(store.get(fid).step, 3)

    def test_corrupt_checkpoint_is_quarantined_and_not_resumed(self):
        with tempfile.TemporaryDirectory() as d:
            db_path = str(Path(d) / "fibers.db")
            store = FiberStore(db_path)
            fid = store.register("corruptible")
            db = sqlite3.connect(db_path)
            try:
                db.execute("UPDATE fibers SET state=? WHERE fiber_id=?", ("{not-json", fid))
                db.commit()
            finally:
                db.close()
            with self.assertRaisesRegex(FiberCorrupt, "checkpoint_corrupt"):
                store.resume(fid, lambda step, state, payload: {"step": step + 1, "state": {}, "done": True})
            self.assertEqual(store.recoverable(), [])
            db = sqlite3.connect(db_path)
            try:
                status, error = db.execute("SELECT status,error FROM fibers WHERE fiber_id=?", (fid,)).fetchone()
            finally:
                db.close()
            self.assertEqual((status, error), ("corrupted", "checkpoint_corrupt"))


if __name__ == "__main__": unittest.main()


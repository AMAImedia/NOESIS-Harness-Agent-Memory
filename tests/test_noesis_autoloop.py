import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.noesis_autoloop import WorkerError, acquire_lock, atomic_write, read_state, release_lock, run_cycle


class NoesisAutoloopTests(unittest.TestCase):
    def test_atomic_state_round_trip(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / ".noesis_autoloop" / "state.json"
            payload = {"schema_version": "noesis.windows-autoloop.v1", "cycle": 4, "status": "passed"}
            atomic_write(path, payload)
            self.assertEqual(read_state(path), payload)
            self.assertFalse(list(path.parent.glob("*.tmp")))

    def test_stale_lock_is_recovered(self):
        with tempfile.TemporaryDirectory() as root:
            lock = Path(root) / "worker.lock"
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text("999999 1\n", encoding="ascii")
            acquire_lock(lock)
            self.assertEqual(lock.read_text(encoding="ascii").split()[0], str(os.getpid()))
            release_lock(lock)
            self.assertFalse(lock.exists())

    def test_live_lock_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            lock = Path(root) / "worker.lock"
            acquire_lock(lock)
            try:
                with self.assertRaisesRegex(WorkerError, "worker_already_running"):
                    acquire_lock(lock)
            finally:
                release_lock(lock)

    def test_once_cycle_persists_passed_result(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            state_path = repo / ".noesis_autoloop" / "state.json"
            log_path = repo / ".noesis_autoloop" / "worker.log"
            command = '"' + sys.executable.replace('"', '') + '" -c pass'
            result = run_cycle(repo, command, 30.0, state_path, log_path)
            self.assertEqual(result["status"], "passed")
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["cycle"], 1)
            self.assertEqual(persisted["status"], "passed")
            self.assertIn("BEGIN", log_path.read_text(encoding="utf-8"))
            self.assertIn("END", log_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

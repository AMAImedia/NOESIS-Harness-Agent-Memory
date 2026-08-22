import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.noesis_autoloop import WorkerError, acquire_lock, atomic_write, capability_status, read_state, release_lock, run_cycle


class NoesisAutoloopTests(unittest.TestCase):
    def test_capability_status_is_explicitly_validation_only(self):
        status = capability_status()
        self.assertEqual(status["schema_version"], "noesis.autoloop-capabilities.v1")
        self.assertTrue(status["worker_persistent"])
        self.assertEqual(status["status"], "validation_only")
        self.assertFalse(status["agent_session_continuity"])
        self.assertFalse(status["autonomous_code_promotion"])
        self.assertFalse(status["autonomous_protected_admin_mutation"])
        self.assertFalse(status["local_inference_configured"])
        self.assertEqual(status["boundary_version"], "protected-actions.v1")
        self.assertEqual(status["evidence_digest"], capability_status()["evidence_digest"])

    def test_capability_status_rejects_blank_configuration(self):
        status = capability_status("  ", "\t", "  ")
        self.assertEqual(status["status"], "validation_only")
        self.assertFalse(status["local_endpoint_configured"])
        self.assertFalse(status["prompt_file_configured"])
        self.assertFalse(status["arbitrary_command_configured"])
        self.assertNotIn("127.0.0.1", json.dumps(status, sort_keys=True))

    def test_capability_status_digest_is_deterministic_and_secret_free(self):
        first = capability_status("http://127.0.0.1:8810/api/chat", "C:\\secret\\prompt.txt", "python worker.py")
        second = capability_status("http://127.0.0.1:8810/api/chat", "C:\\secret\\prompt.txt", "python worker.py")
        self.assertEqual(first, second)
        self.assertNotIn("8810", json.dumps(first, sort_keys=True))
        self.assertNotIn("secret", json.dumps(first, sort_keys=True))

    def test_capability_status_marks_local_inference_review_only(self):
        status = capability_status("http://127.0.0.1:8810", "prompt.txt")
        self.assertEqual(status["status"], "review_only")
        self.assertEqual(status["worker_modes"], ["validation_recovery", "review_only_proposal"])
        self.assertTrue(status["local_inference_configured"])
        self.assertFalse(status["agent_session_continuity"])
        self.assertFalse(status["autonomous_protected_admin_mutation"])

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

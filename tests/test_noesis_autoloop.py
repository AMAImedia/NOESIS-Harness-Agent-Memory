import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.noesis_autoloop import WorkerError, acquire_lock, atomic_write, capability_status, claim_proposal_step, digest, main, read_handoff, read_proposal_queue, read_state, release_lock, run_cycle, select_proposal_step, write_handoff


class NoesisAutoloopTests(unittest.TestCase):
    def test_proposal_queue_selection_is_deterministic_and_bounded(self):
        queue = ["first", "second"]
        path = self._write_json_file(queue)
        try:
            self.assertEqual(read_proposal_queue(path), queue)
            self.assertEqual(select_proposal_step(queue, {"proposal_step_index": 0}), "first")
            self.assertEqual(select_proposal_step(queue, {"proposal_step_index": 1}), "second")
            self.assertIsNone(select_proposal_step(queue, {"proposal_step_index": 2}))
            with self.assertRaisesRegex(WorkerError, "proposal_queue_index_invalid"):
                select_proposal_step(queue, {"proposal_step_index": 3})
        finally:
            os.unlink(path)

    def _write_json_file(self, value):
        handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False)
        try:
            json.dump(value, handle)
            return Path(handle.name)
        finally:
            handle.close()

    def test_proposal_lease_denies_live_duplicate_and_reclaims_expired(self):
        live = {"cycle": 4, "status": "running", "proposal_step_index": 2, "proposal_lease_expires_at": 9999999999}
        with self.assertRaisesRegex(WorkerError, "proposal_step_lease_active"):
            claim_proposal_step(live, 30.0)
        expired = {"cycle": 4, "status": "running", "proposal_step_index": 2, "proposal_lease_expires_at": 1}
        first = claim_proposal_step(expired, 30.0)
        second = claim_proposal_step(expired, 30.0)
        self.assertEqual(first["proposal_step_index"], 2)
        self.assertEqual(second["proposal_step_index"], 2)
        self.assertNotEqual(first["proposal_lease_id"], second["proposal_lease_id"])
        self.assertGreater(first["proposal_lease_expires_at"], 0)

    def test_proposal_queue_rejects_malformed_entries(self):
        path = self._write_json_file(["ok", ""])
        try:
            with self.assertRaisesRegex(WorkerError, "proposal_queue_invalid"):
                read_proposal_queue(path)
        finally:
            os.unlink(path)

    def test_handoff_manifest_is_secret_free_and_bounded(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            result = {"cycle": 8, "status": "passed", "command": "SUPER_SECRET"}
            write_handoff(repo, result)
            handoff = json.loads((repo / ".noesis_autoloop" / "handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(handoff["schema_version"], "noesis.autoloop-handoff.v1")
            self.assertEqual(handoff["source_cycle"], 8)
            self.assertIn("stdlib_code", handoff["allowed"])
            self.assertIn("protected_admin_mutation", handoff["forbidden"])
            handoff_path = repo / ".noesis_autoloop" / "handoff.json"
            self.assertNotIn("SUPER_SECRET", handoff_path.read_text(encoding="utf-8"))
            self.assertEqual(read_handoff(handoff_path)["source_cycle"], 8)
            value = json.loads(handoff_path.read_text(encoding="utf-8"))
            value["unexpected"] = "deny"
            handoff_path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(WorkerError, "handoff_schema_invalid"):
                read_handoff(handoff_path)

    def test_handoff_corruption_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            handoff_path = Path(root) / "handoff.json"
            handoff_path.write_text("{not-json", encoding="utf-8")
            with self.assertRaisesRegex(WorkerError, "handoff_corrupt"):
                read_handoff(handoff_path)

    def test_handoff_schema_and_type_mismatches_fail_closed(self):
        with tempfile.TemporaryDirectory() as root:
            handoff_path = Path(root) / "handoff.json"
            valid = {
                "schema_version": "noesis.autoloop-handoff.v1",
                "source_cycle": 1,
                "source_status": "passed",
                "source_result_digest": "a" * 64,
                "next_action": "inspect_state_then_take_one_bounded_safe_increment",
                "allowed": ["stdlib_code"],
                "forbidden": ["protected_admin_mutation"],
                "created_at": 1.0,
            }
            for field, expected in (("schema_version", "handoff_schema_invalid"), ("source_cycle", "handoff_cycle_invalid"), ("source_result_digest", "handoff_digest_invalid"), ("allowed", "handoff_policy_invalid")):
                value = dict(valid)
                value[field] = {"bad": True} if field != "source_cycle" else -1
                if field == "schema_version":
                    value[field] = "noesis.autoloop-handoff.v0"
                if field == "source_result_digest":
                    value[field] = "short"
                if field == "allowed":
                    value[field] = "stdlib_code"
                handoff_path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaisesRegex(WorkerError, expected):
                    read_handoff(handoff_path)

    def test_stale_handoff_is_replaced_by_next_successful_cycle(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            handoff_path = repo / ".noesis_autoloop" / "handoff.json"
            write_handoff(repo, {"cycle": 1, "status": "passed", "old": "stale"})
            command = '"' + sys.executable.replace('"', '') + '" -c pass'
            state_path = repo / ".noesis_autoloop" / "state.json"
            log_path = repo / ".noesis_autoloop" / "worker.log"
            atomic_write(state_path, {"schema_version": "noesis.windows-autoloop.v1", "cycle": 1, "status": "passed"})
            self.assertEqual(main(["--root", str(repo), "--once", "--command", command, "--timeout", "30"]), 0)
            result = read_state(state_path)
            self.assertEqual(result["cycle"], 2)
            refreshed = read_handoff(handoff_path)
            self.assertEqual(refreshed["source_cycle"], 2)
            self.assertNotEqual(refreshed["source_result_digest"], digest({"cycle": 1, "status": "passed", "old": "stale"}))

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

    def test_crashed_running_cycle_is_explicitly_recovered(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            state_path = repo / ".noesis_autoloop" / "state.json"
            log_path = repo / ".noesis_autoloop" / "worker.log"
            atomic_write(state_path, {"schema_version": "noesis.windows-autoloop.v1", "cycle": 7, "status": "running", "pid": 999999})
            command = '"' + sys.executable.replace('"', '') + '" -c pass'
            result = run_cycle(repo, command, 30.0, state_path, log_path)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["cycle"], 8)
            self.assertEqual(result["recovered_previous_cycle"], 7)
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["recovered_previous_cycle"], 7)
            self.assertIn('"recovered_previous_cycle":7', log_path.read_text(encoding="utf-8"))

    def test_custom_command_text_is_not_persisted(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            state_path = repo / ".noesis_autoloop" / "state.json"
            log_path = repo / ".noesis_autoloop" / "worker.log"
            secret_command = '"' + sys.executable.replace('"', '') + '" -c pass --token SUPER_SECRET'
            result = run_cycle(repo, secret_command, 30.0, state_path, log_path)
            self.assertEqual(result["status"], "passed")
            state_text = state_path.read_text(encoding="utf-8")
            log_text = log_path.read_text(encoding="utf-8")
            self.assertNotIn("SUPER_SECRET", state_text)
            self.assertNotIn("SUPER_SECRET", log_text)
            self.assertIn("command_digest", state_text)

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

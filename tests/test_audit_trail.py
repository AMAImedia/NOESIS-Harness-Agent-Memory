"""Tests for noesis_harness/audit_trail.py

Stdlib-only. Exercises append determinism, idempotency, replay, clean-chain
verification, tamper detection, and missing-file handling.
"""

import os
import tempfile
import unittest

from noesis_harness.audit_trail import AuditTrail, ZERO_DIGEST, _fingerprint


class TestAuditTrail(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "audit.jsonl")

    def test_missing_file_replay_empty_and_verify_true(self):
        trail = AuditTrail(self.path)
        self.assertEqual(trail.replay(), [])
        self.assertTrue(trail.verify())

    def test_append_returns_entry_id(self):
        trail = AuditTrail(self.path)
        eid = trail.append("auth", "login", {"user": "a"})
        self.assertTrue(isinstance(eid, str))
        self.assertEqual(len(eid), 64)

    def test_append_determinism_same_inputs_same_id(self):
        t1 = AuditTrail(self.path)
        t2 = AuditTrail(self.path)
        self.assertEqual(
            t1.append("scope", "act", {"x": 1}),
            t2.append("scope", "act", {"x": 1}),
        )

    def test_fingerprint_key_order_independent(self):
        self.assertEqual(
            _fingerprint("s", "a", {"b": 2, "a": 1}),
            _fingerprint("s", "a", {"a": 1, "b": 2}),
        )

    def test_idempotent_same_entry_id_no_rewrite(self):
        trail = AuditTrail(self.path)
        eid = trail.append("scope", "act", {"v": 1}, entry_id="evt-1")
        again = trail.append("scope", "act", {"v": 1}, entry_id="evt-1")
        self.assertEqual(eid, again)
        self.assertEqual(len(trail.replay()), 1)

    def test_idempotent_same_content_different_idempotent(self):
        trail = AuditTrail(self.path)
        trail.append("scope", "act", {"v": 1})
        trail.append("scope", "act", {"v": 1})
        self.assertEqual(len(trail.replay()), 1)

    def test_replay_returns_all_in_order(self):
        trail = AuditTrail(self.path)
        trail.append("s", "a", {"n": 1})
        trail.append("s", "b", {"n": 2})
        trail.append("s", "c", {"n": 3})
        entries = trail.replay()
        self.assertEqual(len(entries), 3)
        self.assertEqual([e["action"] for e in entries], ["a", "b", "c"])

    def test_verify_true_on_clean_chain(self):
        trail = AuditTrail(self.path)
        trail.append("s", "a", {"n": 1})
        trail.append("s", "b", {"n": 2})
        self.assertTrue(trail.verify())

    def test_verify_false_when_entry_tampered(self):
        trail = AuditTrail(self.path)
        trail.append("s", "a", {"n": 1})
        trail.append("s", "b", {"n": 2})
        # Tamper with the payload of the first entry on disk.
        with open(self.path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        rec = __import__("json").loads(lines[0])
        rec["payload"] = {"n": 999}
        lines[0] = __import__("json").dumps(rec) + "\n"
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
        self.assertFalse(trail.verify())

    def test_verify_false_when_digest_altered(self):
        trail = AuditTrail(self.path)
        trail.append("s", "a", {"n": 1})
        trail.append("s", "b", {"n": 2})
        with open(self.path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        rec = __import__("json").loads(lines[1])
        rec["digest"] = "0" * 64
        lines[1] = __import__("json").dumps(rec) + "\n"
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
        self.assertFalse(trail.verify())

    def test_first_entry_prev_is_zero_digest(self):
        trail = AuditTrail(self.path)
        trail.append("s", "a", {"n": 1})
        self.assertEqual(trail.replay()[0]["prev"], ZERO_DIGEST)

    def test_persistence_across_reload(self):
        trail = AuditTrail(self.path)
        trail.append("s", "a", {"n": 1}, entry_id="e1")
        trail.append("s", "b", {"n": 2}, entry_id="e2")
        reloaded = AuditTrail(self.path)
        self.assertEqual(len(reloaded.replay()), 2)
        self.assertTrue(reloaded.verify())

    def test_idempotent_after_reload(self):
        trail = AuditTrail(self.path)
        trail.append("s", "a", {"n": 1}, entry_id="e1")
        reloaded = AuditTrail(self.path)
        reloaded.append("s", "a", {"n": 1}, entry_id="e1")
        self.assertEqual(len(reloaded.replay()), 1)


if __name__ == "__main__":
    unittest.main()

"""Tests for noesis_harness.attestation (stdlib only)."""

import hashlib
import json
import os
import tempfile
import unittest

from noesis_harness.attestation import AttestationLog, _fingerprint


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class TestAttestation(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "attest.jsonl")
        self.log = AttestationLog(self.path)

    def test_missing_file_treated_empty(self):
        self.assertFalse(os.path.exists(self.path))
        self.assertIsNone(self.log.verify("nobody"))
        self.assertEqual(self.log.replay(), [])

    def test_attest_and_verify(self):
        rec = self.log.attest("agent-a", "deployed", _sha256("proof1"))
        self.assertTrue(os.path.exists(self.path))
        result = self.log.verify("agent-a")
        self.assertIsNotNone(result)
        self.assertEqual(result["claim"], "deployed")
        self.assertEqual(result["evidence_hash"], _sha256("proof1"))
        self.assertEqual(rec["entry_id"], result.get("entry_id", rec["entry_id"]))

    def test_verify_unknown_subject_is_none(self):
        self.log.attest("agent-a", "deployed", _sha256("proof1"))
        self.assertIsNone(self.log.verify("agent-b"))

    def test_replay_returns_written_records(self):
        self.log.attest("s1", "c1", _sha256("e1"))
        self.log.attest("s2", "c2", _sha256("e2"))
        records = self.log.replay()
        self.assertEqual(len(records), 2)
        subjects = sorted(r["subject"] for r in records)
        self.assertEqual(subjects, ["s1", "s2"])

    def test_fingerprint_determinism(self):
        rec = self.log.attest("s", "c", _sha256("e"))
        fp1 = _fingerprint(rec)
        fp2 = _fingerprint(json.loads(json.dumps(rec)))
        self.assertEqual(fp1, fp2)
        self.assertEqual(len(fp1), 64)

    def test_fingerprint_depends_on_content(self):
        r1 = self.log.attest("s", "c1", _sha256("e1"))
        r2 = self.log.attest("s", "c2", _sha256("e2"))
        self.assertNotEqual(_fingerprint(r1), _fingerprint(r2))

    def test_idempotent_same_entry_id(self):
        eid = "fixed-id-123"
        first = self.log.attest("s", "c", _sha256("e"), entry_id=eid)
        second = self.log.attest("s", "c", _sha256("different"), entry_id=eid)
        self.assertEqual(first["entry_id"], second["entry_id"])
        self.assertEqual(self.log.replay(), [first])
        self.assertEqual(len(self.log.replay()), 1)

    def test_verify_latest_wins(self):
        self.log.attest("s", "old", _sha256("e1"))
        self.log.attest("s", "new", _sha256("e2"))
        result = self.log.verify("s")
        self.assertEqual(result["claim"], "new")
        self.assertEqual(result["evidence_hash"], _sha256("e2"))

    def test_tamper_evidence_on_replay(self):
        self.log.attest("s", "c1", _sha256("e1"))
        self.log.attest("s", "c2", _sha256("e2"))
        with open(self.path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        rec = json.loads(lines[0])
        rec["claim"] = "TAMPERED"
        lines[0] = json.dumps(rec) + "\n"
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
        valid = self.log.replay()
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0]["claim"], "c2")

    def test_tamper_evidence_on_verify(self):
        self.log.attest("s", "c1", _sha256("e1"))
        with open(self.path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        rec = json.loads(lines[0])
        rec["evidence_hash"] = _sha256("forged")
        lines[0] = json.dumps(rec) + "\n"
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
        self.assertIsNone(self.log.verify("s"))

    def test_multiple_subjects_independent(self):
        self.log.attest("a", "ca", _sha256("ea"))
        self.log.attest("b", "cb", _sha256("eb"))
        self.log.attest("a", "ca2", _sha256("ea2"))
        self.assertEqual(self.log.verify("a")["claim"], "ca2")
        self.assertEqual(self.log.verify("b")["claim"], "cb")
        self.assertEqual(len(self.log.replay()), 3)

    def test_attest_creates_parent_dir(self):
        nested = os.path.join(self.tmp, "nested", "deep", "attest.jsonl")
        log = AttestationLog(nested)
        log.attest("s", "c", _sha256("e"))
        self.assertTrue(os.path.exists(nested))


if __name__ == "__main__":
    unittest.main()

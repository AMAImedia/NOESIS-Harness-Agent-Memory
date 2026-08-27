"""tests/test_seal_log.py

Unit tests for noesis_harness.seal_log (stdlib-only, append-only seal log).
"""

import os
import tempfile
import unittest

from noesis_harness.seal_log import SealLog, ZERO_DIGEST


class TestSealLog(unittest.TestCase):
    def setUp(self):
        self._fh = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        self._fh.close()
        self.path = self._fh.name

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_seal_and_head(self):
        log = SealLog(self.path)
        eid = log.seal("checkpoint", {"step": 1})
        head = log.head()
        self.assertIsNotNone(head)
        self.assertEqual(head["label"], "checkpoint")
        self.assertEqual(head["payload"], {"step": 1})
        self.assertEqual(head["entry_id"], eid)

    def test_head_none_when_empty(self):
        log = SealLog(self.path)
        self.assertIsNone(log.head())

    def test_verify_true_on_clean_log(self):
        log = SealLog(self.path)
        log.seal("a", {"x": 1})
        log.seal("b", {"y": 2})
        log.seal("c", "plain string")
        self.assertTrue(log.verify())
        self.assertEqual(len(log), 3)

    def test_verify_false_on_tamper(self):
        log = SealLog(self.path)
        log.seal("a", {"x": 1})
        log.seal("b", {"y": 2})
        self.assertTrue(log.verify())

        with open(self.path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        rec = __import__("json").loads(lines[0])
        rec["payload"] = {"x": 999}
        lines[0] = __import__("json").dumps(rec, ensure_ascii=False) + "\n"
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)

        self.assertFalse(SealLog(self.path).verify())

    def test_verify_false_on_prev_digest_tamper(self):
        log = SealLog(self.path)
        log.seal("a", {"x": 1})
        log.seal("b", {"y": 2})
        with open(self.path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        rec = __import__("json").loads(lines[1])
        rec["prev_digest"] = ZERO_DIGEST
        lines[1] = __import__("json").dumps(rec, ensure_ascii=False) + "\n"
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
        self.assertFalse(SealLog(self.path).verify())

    def test_idempotent_resend(self):
        log = SealLog(self.path)
        eid1 = log.seal("a", {"x": 1})
        eid2 = log.seal("a", {"x": 1})
        self.assertEqual(eid1, eid2)
        self.assertEqual(len(log), 1)
        self.assertTrue(log.verify())

    def test_idempotent_with_explicit_entry_id(self):
        log = SealLog(self.path)
        eid = log.seal("a", {"x": 1}, entry_id="fixed-id")
        eid2 = log.seal("a", {"x": 1}, entry_id="fixed-id")
        self.assertEqual(eid, "fixed-id")
        self.assertEqual(eid2, "fixed-id")
        self.assertEqual(len(log), 1)

    def test_chain_advances(self):
        log = SealLog(self.path)
        e1 = log.seal("a", {"x": 1})
        e2 = log.seal("b", {"x": 2})
        self.assertNotEqual(e1, e2)
        first = SealLog(self.path)._load()[0]
        head = log.head()
        self.assertEqual(head["entry_id"], e2)
        self.assertEqual(head["prev_digest"], first["self_digest"])
        self.assertEqual(first["prev_digest"], ZERO_DIGEST)

    def test_missing_file_is_clean(self):
        missing = self.path + ".nonexistent"
        if os.path.exists(missing):
            os.remove(missing)
        log = SealLog(missing)
        self.assertTrue(log.verify())
        self.assertIsNone(log.head())
        self.assertEqual(len(log), 0)
        eid = log.seal("first", {})
        self.assertTrue(os.path.exists(missing))
        self.assertEqual(log.head()["entry_id"], eid)
        os.remove(missing)

    def test_verify_does_not_mutate_file(self):
        log = SealLog(self.path)
        log.seal("a", {"x": 1})
        log.seal("b", {"y": 2})
        with open(self.path, "rb") as fh:
            before = __import__("hashlib").sha256(fh.read()).hexdigest()
        self.assertTrue(log.verify())
        with open(self.path, "rb") as fh:
            after = __import__("hashlib").sha256(fh.read()).hexdigest()
        self.assertEqual(before, after)

    def test_payload_variants(self):
        log = SealLog(self.path)
        log.seal("str", "hello")
        log.seal("int", 42)
        log.seal("list", [1, 2, 3])
        log.seal("nested", {"a": {"b": [1, 2]}})
        log.seal("none", None)
        self.assertTrue(log.verify())
        self.assertEqual(len(log), 5)
        self.assertEqual(log.head()["payload"], None)

    def test_separate_instances_same_file_consistent(self):
        log1 = SealLog(self.path)
        log1.seal("a", {"x": 1})
        log2 = SealLog(self.path)
        log2.seal("b", {"x": 2})
        self.assertEqual(len(log1), 2)
        self.assertEqual(len(log2), 2)
        self.assertTrue(log1.verify())
        self.assertTrue(log2.verify())
        self.assertEqual(log2.head()["label"], "b")


if __name__ == "__main__":
    unittest.main()

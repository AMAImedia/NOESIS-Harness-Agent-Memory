"""Tests for noesis_harness/holder_registry.py

Stdlib-only. Exercises the append-only holder registry: registration, active
holder resolution, scope filtering, replay, idempotency, deterministic
fingerprinting, de-duplication, missing-file resilience, and no-mutation of
caller inputs.
"""

import os
import tempfile
import unittest

from noesis_harness.holder_registry import HolderRegistry, fingerprint


class HolderRegistryTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="holder_reg_test_")
        self.path = os.path.join(self.dir, "registry.jsonl")

    def test_register_and_active(self):
        reg = HolderRegistry(self.path)
        reg.register("agent-a", "scope-x")
        reg.register("agent-b", "scope-x")
        self.assertEqual(set(reg.active_holders()), {"agent-a", "agent-b"})

    def test_scope_filter(self):
        reg = HolderRegistry(self.path)
        reg.register("agent-a", "scope-x")
        reg.register("agent-b", "scope-y")
        self.assertEqual(reg.active_holders("scope-x"), ["agent-a"])
        self.assertEqual(reg.active_holders("scope-y"), ["agent-b"])
        self.assertEqual(set(reg.active_holders()), {"agent-a", "agent-b"})

    def test_replay_returns_all_records_in_order(self):
        reg = HolderRegistry(self.path)
        reg.register("agent-a", "scope-x")
        reg.register("agent-b", "scope-x")
        recs = reg.replay()
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0]["holder"], "agent-a")
        self.assertEqual(recs[1]["holder"], "agent-b")
        for rec in recs:
            self.assertIn("entry_id", rec)
            self.assertIn("fingerprint", rec)
            self.assertIn("ts", rec)

    def test_idempotent_same_entry_id(self):
        reg = HolderRegistry(self.path)
        eid = reg.register("agent-a", "scope-x", entry_id="evt-1")
        self.assertEqual(eid, "evt-1")
        eid2 = reg.register("agent-a", "scope-x", entry_id="evt-1")
        self.assertEqual(eid2, "evt-1")
        # double-send must not create a duplicate line
        self.assertEqual(len(reg.replay()), 1)

    def test_idempotent_same_content_auto_id(self):
        reg = HolderRegistry(self.path)
        reg.register("agent-a", "scope-x")
        reg.register("agent-a", "scope-x")  # same fingerprint auto-id
        self.assertEqual(len(reg.replay()), 1)

    def test_fingerprint_determinism(self):
        fp1 = fingerprint("agent-a", "scope-x")
        fp2 = fingerprint("agent-a", "scope-x")
        fp3 = fingerprint("agent-b", "scope-x")
        self.assertEqual(fp1, fp2)
        self.assertIsInstance(fp1, str)
        self.assertEqual(len(fp1), 64)
        self.assertNotEqual(fp1, fp3)

    def test_dedup_across_reloaded_registry(self):
        reg = HolderRegistry(self.path)
        reg.register("agent-a", "scope-x")
        reg2 = HolderRegistry(self.path)  # reload replays existing log
        reg2.register("agent-a", "scope-x")
        self.assertEqual(len(reg2.replay()), 1)

    def test_missing_file_active_empty(self):
        # path does not exist yet
        reg = HolderRegistry(self.path)
        self.assertEqual(reg.active_holders(), [])
        self.assertEqual(reg.active_holders("scope-x"), [])
        self.assertEqual(reg.replay(), [])

    def test_register_creates_missing_file(self):
        self.assertFalse(os.path.exists(self.path))
        reg = HolderRegistry(self.path)
        reg.register("agent-a", "scope-x")
        self.assertTrue(os.path.exists(self.path))
        self.assertEqual(reg.active_holders(), ["agent-a"])

    def test_no_mutation_of_inputs(self):
        reg = HolderRegistry(self.path)
        holder = ["agent-a"]  # mutable input
        scope = {"name": "scope-x"}  # mutable input
        reg.register(holder, scope)  # type: ignore[arg-type]
        # the registry must stringify, not mutate, the caller's objects
        self.assertEqual(holder, ["agent-a"])
        self.assertEqual(scope, {"name": "scope-x"})
        recs = reg.replay()
        self.assertEqual(recs[0]["holder"], "['agent-a']")
        self.assertEqual(recs[0]["scope"], "{'name': 'scope-x'}")

    def test_latest_wins_per_holder_scope(self):
        reg = HolderRegistry(self.path)
        reg.register("agent-a", "scope-x")
        reg.register("agent-a", "scope-x")  # refresh, not a new holder
        self.assertEqual(reg.active_holders("scope-x"), ["agent-a"])
        self.assertEqual(len(reg.active_holders("scope-x")), 1)

    def test_reused_entry_id_different_content_raises(self):
        reg = HolderRegistry(self.path)
        reg.register("agent-a", "scope-x", entry_id="evt-1")
        with self.assertRaises(ValueError):
            reg.register("agent-b", "scope-x", entry_id="evt-1")

    def test_active_holders_preserves_order(self):
        reg = HolderRegistry(self.path)
        reg.register("agent-c", "scope-x")
        reg.register("agent-a", "scope-x")
        reg.register("agent-b", "scope-x")
        self.assertEqual(
            reg.active_holders("scope-x"), ["agent-c", "agent-a", "agent-b"]
        )


if __name__ == "__main__":
    unittest.main()

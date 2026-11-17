import tempfile
import unittest
from pathlib import Path

from noesis_harness.resource_lineage import LineageError, Observation, ObservationLedger


class ResourceLineageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = ObservationLedger(str(Path(self.tmp.name) / "events.jsonl"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_observation_is_idempotent_and_does_not_store_content(self):
        observation = Observation("s", "agent-a", "warehouse:customers", "warehouse", "sensitive", self.ledger.digest_content("private row"))
        first = self.ledger.record(observation)
        second = self.ledger.record(observation)
        self.assertEqual(first, second)
        rows = self.ledger.observations("s", "agent-a")
        self.assertEqual(len(rows), 1)
        self.assertNotIn("private row", str(rows[0]))

    def test_sensitive_observation_blocks_egress_until_approval(self):
        self.ledger.record(Observation("s", "agent-a", "vault:customers", "vault", "restricted"))
        denied = self.ledger.decide_egress("s", "agent-a", "external:webhook")
        self.assertFalse(denied.allowed)
        self.assertEqual(denied.reason, "tainted_by_observed_resource")
        allowed = self.ledger.decide_egress("s", "agent-a", "external:webhook", explicit_approval=True)
        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.reason, "explicit_approval")

    def test_invalid_sensitivity_fails_closed(self):
        with self.assertRaises(LineageError):
            self.ledger.record(Observation("s", "agent-a", "x", "source", "secret"))

    def test_parent_chain_requires_same_session_and_cannot_downgrade(self):
        parent = self.ledger.record(Observation("s", "agent-a", "vault:row", "vault", "restricted"))
        child = self.ledger.record(Observation("s", "agent-b", "derived:row", "transform", "restricted", parent_observation=parent))
        self.assertTrue(child)
        with self.assertRaises(LineageError):
            self.ledger.record(Observation("s", "agent-b", "leak:row", "transform", "public", parent_observation=parent))
        with self.assertRaises(LineageError):
            self.ledger.record(Observation("other", "agent-b", "derived:row", "transform", "restricted", parent_observation=parent))

    def test_cross_agent_derived_taint_blocks_egress(self):
        parent = self.ledger.record(Observation("s", "agent-a", "vault:row", "vault", "sensitive"))
        self.ledger.record(Observation("s", "agent-b", "derived:row", "transform", "sensitive", parent_observation=parent))
        decision = self.ledger.decide_egress("s", "agent-b", "external:webhook")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "tainted_by_observed_resource")
        self.assertIn("derived:row", decision.observed_resources)


if __name__ == "__main__":
    unittest.main()

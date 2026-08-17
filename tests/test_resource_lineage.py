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


if __name__ == "__main__":
    unittest.main()

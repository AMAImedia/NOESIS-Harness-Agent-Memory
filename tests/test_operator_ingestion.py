import tempfile
import time
import unittest

from scripts.build_operator_case_bundle import build_bundle
from scripts.operator_ingestion import OperatorIngestionLedger
from tests.test_external_evidence_readiness import evidence_for, manifest


class OperatorIngestionTests(unittest.TestCase):
    KEY = "operator-ingestion-test-key"

    def setup_bundle(self):
        evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        value = manifest(protocol_fingerprint=evidence[0]["protocol_fingerprint"], case_ids=["case-a"])
        value["revisions"] = {"hermes": "h1", "opencode": "o1", "deepseek_harness": "d1"}
        return value, evidence, build_bundle(value)

    def test_preflight_requires_explicit_approval_and_never_executes(self):
        value, _, bundle = self.setup_bundle()
        with tempfile.TemporaryDirectory() as directory:
            ledger = OperatorIngestionLedger(directory + "/ledger.sqlite")
            record = ledger.preflight(bundle, value)
            self.assertEqual(record["state"], "awaiting_approval")
            self.assertFalse(record["execution_allowed"])
            self.assertFalse(record["automatic_execution"])
            with self.assertRaises(ValueError):
                ledger.import_result(record["record_id"], {}, self.KEY, bundle, value, [], [])

    def test_signed_approval_and_import_are_durable(self):
        value, evidence, bundle = self.setup_bundle()
        with tempfile.TemporaryDirectory() as directory:
            ledger = OperatorIngestionLedger(directory + "/ledger.sqlite")
            record = ledger.preflight(bundle, value)
            approval = ledger.approve(record["record_id"], self.KEY, operator_id="operator-1", now=time.time())
            # Import is intentionally accepted_not_run because external evidence is not supplied here.
            result = ledger.import_result(record["record_id"], approval, self.KEY, bundle, value, [], [])
            self.assertEqual(result["state"], "imported")
            self.assertEqual(result["result"]["status"], "accepted_not_run")
            status = ledger.status(record["record_id"])
            self.assertEqual(status["state"], "imported")
            self.assertFalse(status["external_execution_claim"])
            self.assertFalse(status["score_claim"])

    def test_approval_replay_and_stale_identity_are_rejected(self):
        value, evidence, bundle = self.setup_bundle()
        with tempfile.TemporaryDirectory() as directory:
            ledger = OperatorIngestionLedger(directory + "/ledger.sqlite")
            record = ledger.preflight(bundle, value)
            approval = ledger.approve(record["record_id"], self.KEY, operator_id="operator-1", now=time.time())
            ledger.import_result(record["record_id"], approval, self.KEY, bundle, value, [], [])
            with self.assertRaises(ValueError):
                ledger.import_result(record["record_id"], approval, self.KEY, bundle, value, [], [])

    def test_drift_is_blocked_after_approval(self):
        value, _, bundle = self.setup_bundle()
        with tempfile.TemporaryDirectory() as directory:
            ledger = OperatorIngestionLedger(directory + "/ledger.sqlite")
            record = ledger.preflight(bundle, value)
            approval = ledger.approve(record["record_id"], self.KEY, operator_id="operator-1", now=time.time())
            changed = dict(value)
            changed["case_ids"] = ["drifted"]
            result = ledger.import_result(record["record_id"], approval, self.KEY, bundle, changed, [], [])
            self.assertEqual(result["state"], "blocked")
            self.assertEqual(result["result"]["status"], "blocked")


if __name__ == "__main__":
    unittest.main()

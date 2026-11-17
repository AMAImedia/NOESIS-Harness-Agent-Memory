import tempfile
import unittest
from pathlib import Path

from scripts.transfer_audit import audit_transfer_set


REQUIRED = (
    "artifact-manifest.json",
    "external-evidence-readiness.json",
    "signed-external-evidence-aggregate.json",
    "verification-result.json",
    "chain-summary.json",
    "reproducibility-receipt.json",
)

COMMITTED_EVIDENCE = (
    "MULTI_AGENT_WORKLOAD_EVIDENCE.json",
    "PARALLEL_RELEASE_AUDIT_EVIDENCE.json",
)


class TransferAuditTests(unittest.TestCase):
    def populate(self, root):
        for name in REQUIRED:
            (root / name).write_text("{}\n", encoding="utf-8")

    def test_expected_composition_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            report = root / "operator-report.zip"
            report.write_bytes(b"zip-placeholder")
            result = audit_transfer_set(root, str(report))
            self.assertEqual(result["status"], "passed")
            self.assertFalse(result["automatic_execution"])

    def test_registered_committed_evidence_names_are_optional_members(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            for name in COMMITTED_EVIDENCE:
                (root / name).write_text("{}\n", encoding="utf-8")
            result = audit_transfer_set(root)
            self.assertEqual(result["status"], "passed")
            for name in COMMITTED_EVIDENCE:
                self.assertIn(name, result["present"])
                self.assertIn(name, result["optional"])

    def test_missing_and_unexpected_files_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            (root / "chain-summary.json").unlink()
            self.assertEqual(audit_transfer_set(root)["reason"], "transfer_required_artifact_missing")
            self.populate(root)
            (root / "debug.log").write_text("unexpected", encoding="utf-8")
            self.assertEqual(audit_transfer_set(root)["reason"], "transfer_unexpected_artifact")

    def test_report_must_be_bounded_and_named(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            outside = Path(directory).parent / "outside-report.zip"
            outside.write_bytes(b"x")
            try:
                self.assertEqual(audit_transfer_set(root, str(outside))["reason"], "transfer_report_invalid")
            finally:
                outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

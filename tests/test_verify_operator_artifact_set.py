import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_operator_evidence_pipeline import run_pipeline
from scripts.signed_readiness_receipt import sign_readiness_receipt
from scripts.release_gate_artifact import build_gate_artifact
from scripts.verify_operator_artifact_set import verify_artifact_set
from tests.test_external_evidence_readiness import evidence_for, manifest

KEY = "readiness-test-key-2026"


class VerifyOperatorArtifactSetTests(unittest.TestCase):
    def write(self, path, value):
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def build_set(self, root, with_report=True):
        evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        manifest_path = root / "manifest.json"
        self.write(manifest_path, manifest(protocol_fingerprint=evidence[0]["protocol_fingerprint"]))
        paths = []
        for index, record in enumerate(evidence):
            path = root / ("evidence-%d.json" % index)
            self.write(path, record)
            paths.append(str(path))
        snapshot = root / "snapshot.json"
        self.write(snapshot, {"local_execution": {"status": "passed"}, "native_parity": {"status": "not_run"}, "external_comparative": {"status": "not_run"}})
        report = root / "artifacts" / "report.zip" if with_report else None
        artifact_root = root / "artifacts"
        run_pipeline(str(manifest_path), paths, KEY, str(artifact_root), str(snapshot), str(report) if report else None)
        readiness_snapshot = {"schema_version": "noesis.release-readiness-snapshot.v1", "overall_status": "passed", "snapshot_digest": "verifier-snapshot-fixture", "native_host_status": "not_run", "external_lanes_status": "not_run"}
        gate = build_gate_artifact({"status": "passed", "stages": {"post_transfer_audit": {"status": "passed"}, "release_readiness_snapshot": {"status": "passed"}}})
        self.write(artifact_root / "release-readiness.json", readiness_snapshot)
        self.write(artifact_root / "release-gate.json", gate)
        self.write(artifact_root / "signed-readiness-receipt.json", sign_readiness_receipt(readiness_snapshot, gate, 0, "3.14.7", KEY))
        return artifact_root, report

    def test_valid_transferred_set_and_report_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, report = self.build_set(Path(directory))
            result = verify_artifact_set(artifact_root, KEY, str(report))
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["checks"]["inventory"]["status"], "passed")
            self.assertEqual(result["checks"]["report_bundle"]["status"], "passed")
            self.assertFalse(result["automatic_execution"])
            self.assertEqual(result["checks"]["signed_verification_result"]["status"], "passed")
            self.assertEqual(result["checks"]["signed_result_binding"]["status"], "passed")

    def test_tampering_inventory_listed_file_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, _ = self.build_set(Path(directory), with_report=False)
            target = artifact_root / "signed-external-evidence-aggregate.json"
            target.write_text(target.read_text(encoding="utf-8").replace("signed-external", "tampered-external"), encoding="utf-8")
            result = verify_artifact_set(artifact_root, KEY)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["checks"]["inventory"]["reason"], "inventory_file_mismatch")

    def test_signed_result_tampering_and_binding_drift_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root, _ = self.build_set(root, with_report=False)
            result_path = artifact_root / "verification-result.json"
            signed = json.loads(result_path.read_text(encoding="utf-8"))
            signed["verification_status"] = "blocked"
            result_path.write_text(json.dumps(signed), encoding="utf-8")
            result = verify_artifact_set(artifact_root, KEY)
            self.assertEqual(result["checks"]["signed_verification_result"]["reason"], "verification_result_digest_mismatch")
            signed = json.loads(result_path.read_text(encoding="utf-8"))
            signed["verification_status"] = "passed"
            signed["inventory_digest"] = "0" * 64
            import hashlib
            import hmac
            canonical = json.dumps({key: value for key, value in signed.items() if key not in {"result_digest", "signature"}}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            signed["result_digest"] = hashlib.sha256(canonical).hexdigest()
            signed["signature"] = hmac.new(KEY.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
            result_path.write_text(json.dumps(signed), encoding="utf-8")
            result = verify_artifact_set(artifact_root, KEY)
            self.assertEqual(result["checks"]["signed_result_binding"]["reason"], "verification_inventory_digest_mismatch")

    def test_strict_mode_requires_signed_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact_root, _ = self.build_set(root, with_report=False)
            (artifact_root / "verification-result.json").unlink()
            result = verify_artifact_set(artifact_root, KEY, require_signed_result=True)
            self.assertEqual(result["checks"]["transfer_composition"]["reason"], "transfer_required_artifact_missing")
            legacy = verify_artifact_set(artifact_root, KEY)
            self.assertEqual(legacy["status"], "passed")

    def test_strict_mode_missing_readiness_receipt_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, _ = self.build_set(Path(directory), with_report=False)
            (artifact_root / "signed-readiness-receipt.json").unlink()
            result = verify_artifact_set(artifact_root, KEY, require_signed_result=True)
            self.assertEqual(result["checks"]["transfer_composition"]["reason"], "transfer_readiness_receipt_missing")

    def test_tampered_readiness_receipt_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, _ = self.build_set(Path(directory), with_report=False)
            receipt_path = artifact_root / "signed-readiness-receipt.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            receipt["readiness_status"] = "blocked"
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            result = verify_artifact_set(artifact_root, KEY, require_signed_result=True)
            self.assertEqual(result["checks"]["signed_readiness_receipt"]["reason"], "readiness_receipt_digest_mismatch")

    def test_readiness_snapshot_drift_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, _ = self.build_set(Path(directory), with_report=False)
            snapshot_path = artifact_root / "release-readiness.json"
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            snapshot["snapshot_digest"] = "drifted-snapshot"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            result = verify_artifact_set(artifact_root, KEY, require_signed_result=True)
            self.assertEqual(result["checks"]["signed_readiness_receipt"]["reason"], "readiness_receipt_snapshot_drift")

    def test_missing_manifest_and_outside_report_are_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = verify_artifact_set(root, KEY)
            self.assertEqual(result["reason"], "artifact_manifest_missing")
            artifact_root, _ = self.build_set(root, with_report=False)
            outside = root / "outside.zip"
            outside.write_bytes(b"not-a-bundle")
            result = verify_artifact_set(artifact_root, KEY, str(outside))
            self.assertEqual(result["reason"], "report_path_invalid")


if __name__ == "__main__":
    unittest.main()

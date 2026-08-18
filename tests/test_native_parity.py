import sys
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from noesis_harness.native_parity import operator_bundle, prepare_native_evidence, validate_native_artifacts


class NativeParityTests(unittest.TestCase):
    def test_unsupported_target_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "unsupported_native_target"):
            prepare_native_evidence("linux", current_platform="linux", python_version=(3, 14, 7))
        with self.assertRaisesRegex(ValueError, "unsupported_native_target"):
            validate_native_artifacts("linux", ".", current_platform="linux", python_version=(3, 14, 7))

    def test_python_mismatch_never_validates_native(self):
        evidence = prepare_native_evidence("windows", current_platform="win32", python_version=(3, 13, 7))
        self.assertEqual(evidence.status, "not_run")
        self.assertEqual(evidence.reason, "target_host_or_python_mismatch")
        self.assertFalse(evidence.execution_claim)

    def test_linux_preparation_never_claims_native_pass(self):
        for target in ("windows", "macos"):
            evidence = prepare_native_evidence(target, current_platform="linux", python_version=(3, 14, 7))
            self.assertEqual(evidence.status, "not_run")
            self.assertFalse(evidence.execution_claim)
            self.assertEqual(evidence.reason, "target_host_or_python_mismatch")

    def test_matching_platform_still_requires_contract_execution(self):
        evidence = prepare_native_evidence("windows", current_platform="win32", python_version=(3, 14, 7))
        self.assertEqual(evidence.status, "not_run")
        self.assertFalse(evidence.execution_claim)
        self.assertEqual(evidence.reason, "parity_contract_not_executed")

    def test_missing_artifacts_are_blocked_on_matching_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = validate_native_artifacts("windows", tmp, current_platform="win32", python_version=(3, 14, 7))
            self.assertEqual(evidence.status, "blocked")
            self.assertTrue(evidence.reason.startswith("missing_required_artifact:"))
            self.assertFalse(evidence.execution_claim)

    def test_malformed_and_guard_failed_artifacts_are_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("environment.json", "parity-results.json", "sha256sums.txt", "sbom.json"):
                (root / name).write_text("{}" if name.endswith(".json") else "digest  file\n", encoding="utf-8")
            evidence = validate_native_artifacts("macos", root, current_platform="darwin", python_version=(3, 14, 7))
            self.assertEqual(evidence.status, "blocked")
            self.assertEqual(evidence.reason, "environment_guard_failed")

    def test_valid_artifact_shape_can_pass_only_on_matching_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "environment.json").write_text(json.dumps({"target": "windows", "network_allowed": False, "credentials_available": False}), encoding="utf-8")
            (root / "parity-results.json").write_text(json.dumps({"target": "windows", "status": "passed", "execution_claim": True}), encoding="utf-8")
            manifest = "\n".join(hashlib.sha256((root / name).read_bytes()).hexdigest() + "  " + name for name in ("environment.json", "parity-results.json")) + "\n"
            (root / "sha256sums.txt").write_text(manifest, encoding="utf-8")
            (root / "sbom.json").write_text(json.dumps({"files": ["environment.json", "parity-results.json", "sha256sums.txt"]}), encoding="utf-8")
            evidence = validate_native_artifacts("windows", root, current_platform="win32", python_version=(3, 14, 7))
            self.assertEqual(evidence.status, "passed")
            self.assertTrue(evidence.execution_claim)

    def test_stale_or_not_run_parity_result_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "environment.json").write_text(json.dumps({"target": "windows", "network_allowed": False, "credentials_available": False}), encoding="utf-8")
            (root / "parity-results.json").write_text(json.dumps({"target": "windows", "status": "not_run", "execution_claim": False}), encoding="utf-8")
            manifest = "\n".join(hashlib.sha256((root / name).read_bytes()).hexdigest() + "  " + name for name in ("environment.json", "parity-results.json")) + "\n"
            (root / "sha256sums.txt").write_text(manifest, encoding="utf-8")
            (root / "sbom.json").write_text(json.dumps({"files": ["environment.json", "parity-results.json", "sha256sums.txt"]}), encoding="utf-8")
            evidence = validate_native_artifacts("windows", root, current_platform="win32", python_version=(3, 14, 7))
            self.assertEqual(evidence.status, "blocked")
            self.assertEqual(evidence.reason, "parity_result_not_passed")

    def test_sha256_manifest_mismatch_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "environment.json").write_text(json.dumps({"target": "windows", "network_allowed": False, "credentials_available": False}), encoding="utf-8")
            (root / "parity-results.json").write_text(json.dumps({"target": "windows", "status": "passed", "execution_claim": True}), encoding="utf-8")
            (root / "sha256sums.txt").write_text("0" * 64 + "  environment.json\n", encoding="utf-8")
            (root / "sbom.json").write_text(json.dumps({"files": ["environment.json", "parity-results.json", "sha256sums.txt"]}), encoding="utf-8")
            evidence = validate_native_artifacts("windows", root, current_platform="win32", python_version=(3, 14, 7))
            self.assertEqual(evidence.status, "blocked")
            self.assertEqual(evidence.reason, "sha256_manifest_mismatch:environment.json")

    def test_operator_bundles_are_network_off_and_artifact_explicit(self):
        for target in ("windows", "macos"):
            bundle = operator_bundle(target)
            self.assertFalse(bundle["network_allowed"])
            self.assertFalse(bundle["credentials_required"])
            self.assertIn("environment.json", bundle["required_artifacts"])
            self.assertEqual(bundle["status_rule"], "not_run_is_not_passed")
            self.assertEqual(bundle["validator"], "validate_native_artifacts")
            self.assertEqual(bundle["integrity_rule"], "environment_and_parity_sha256_must_match_manifest")


if __name__ == "__main__":
    unittest.main()

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.release_audit import audit


class ReleaseAuditOfflineTests(unittest.TestCase):
    def test_offline_mode_never_calls_ls_remote(self):
        def fake_check_output(command, **kwargs):
            if command[:2] == ["git", "ls-remote"]:
                raise AssertionError("offline audit attempted network parity")
            if command[:2] == ["git", "rev-parse"]:
                return "0123456789abcdef0123456789abcdef01234567\n"
            if command[:2] == ["git", "cat-file"]:
                return ""
            if command[:2] == ["git", "merge-base"]:
                return ""
            if command[:2] == ["git", "status"]:
                return ""
            raise AssertionError(command)

        with patch("scripts.release_audit.subprocess.check_output", side_effect=fake_check_output):
            report = audit(include_remote=False)
        self.assertEqual(report["mode"], "offline")
        self.assertIsNone(report["remote_sha"])
        self.assertIsNone(report["remote_matches_local"])
        self.assertEqual(report["actual_ast_eval_exec_calls"], [])
        self.assertEqual(report["secret_like_hits"], [])
        self.assertEqual(report["syntax_errors"], [])
        self.assertTrue(report["clean"])

    def test_invalid_roadmap_checkpoint_is_audit_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "noesis_harness").mkdir()
            (root / "docs").mkdir()
            (root / "docs" / "ROADMAP_RECONCILIATION_EVIDENCE.json").write_text('{"schema_version":"noesis.roadmap-reconciliation.v1","checkpoint_commit":"old","status":"local_reconciliation_and_next03_bounded_verified"}', encoding="utf-8")

            def fake_check_output(command, **kwargs):
                if command[:2] == ["git", "rev-parse"]:
                    return "current\\n"
                if command[:2] == ["git", "status"]:
                    return ""
                raise AssertionError(command)

            with patch("scripts.release_audit.subprocess.check_output", side_effect=fake_check_output):
                report = audit(str(root), include_remote=False)
            self.assertFalse(report["clean"])
            self.assertIn("roadmap_checkpoint_invalid", report["roadmap_consistency"]["errors"])

    def test_divergent_roadmap_checkpoint_is_audit_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "noesis_harness").mkdir()
            (root / "docs").mkdir()
            (root / "docs" / "ROADMAP_RECONCILIATION_EVIDENCE.json").write_text('{"schema_version":"noesis.roadmap-reconciliation.v1","checkpoint_commit":"1111111111111111111111111111111111111111","status":"local_reconciliation_and_next03_bounded_verified"}', encoding="utf-8")

            def fake_check_output(command, **kwargs):
                if command[:2] == ["git", "rev-parse"]:
                    return "2222222222222222222222222222222222222222\\n"
                if command[:2] == ["git", "cat-file"]:
                    return ""
                if command[:2] == ["git", "merge-base"]:
                    raise subprocess.CalledProcessError(1, command)
                if command[:2] == ["git", "status"]:
                    return ""
                raise AssertionError(command)

            with patch("scripts.release_audit.subprocess.check_output", side_effect=fake_check_output):
                report = audit(str(root), include_remote=False)
            self.assertFalse(report["clean"])
            self.assertIn("roadmap_checkpoint_not_ancestor", report["roadmap_consistency"]["errors"])

    def test_tampered_readiness_digest_is_audit_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "noesis_harness").mkdir()
            (root / "docs").mkdir()
            readiness = {
                "schema_version": "noesis.external-evidence-readiness.v1",
                "comparative_ready": False,
                "overall_status": "not_run",
                "execution_claim": "not_run",
                "native_or_external_execution_claim": False,
                "global_checks": ["comparative_readiness_not_met"],
                "lanes": {"hermes": {"status": "not_run"}},
                "matrix_digest": "0" * 64,
            }
            (root / "docs" / "EXTERNAL_EVIDENCE_READINESS_MATRIX.json").write_text(json.dumps(readiness), encoding="utf-8")

            def fake_check_output(command, **kwargs):
                if command[:2] == ["git", "rev-parse"]:
                    return "0123456789abcdef0123456789abcdef01234567\\n"
                if command[:2] == ["git", "status"]:
                    return ""
                raise AssertionError(command)

            with patch("scripts.release_audit.subprocess.check_output", side_effect=fake_check_output):
                report = audit(str(root), include_remote=False)
            self.assertFalse(report["clean"])
            self.assertIn("readiness_digest_mismatch", report["external_readiness"]["errors"])

    def test_secret_like_content_is_audit_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "noesis_harness"
            package.mkdir()
            (package / "unsafe.py").write_text("TOKEN = 'ghp_12345678901234567890'\n", encoding="utf-8")

            def fake_check_output(command, **kwargs):
                if command[:2] == ["git", "rev-parse"]:
                    return "0123456789abcdef0123456789abcdef01234567\n"
                if command[:2] == ["git", "status"]:
                    return ""
                raise AssertionError(command)

            with patch("scripts.release_audit.subprocess.check_output", side_effect=fake_check_output):
                report = audit(str(root), include_remote=False)
            self.assertFalse(report["clean"])
            self.assertEqual(len(report["secret_like_hits"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

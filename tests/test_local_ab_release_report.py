from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_local_ab_release_report import build, verify_report
from scripts.run_local_signed_ab_fixture import FIXTURE_KEY


class LocalABReleaseReportTests(unittest.TestCase):
    def test_release_report_has_provenance_and_audit_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            output = str(Path(directory) / "release-report.json")
            report = build(output, FIXTURE_KEY)
            self.assertEqual(report["schema_version"], "noesis.local-ab-release.v1")
            self.assertTrue(report["simulation_only"])
            self.assertTrue(report["evaluation"]["comparable"])
            self.assertFalse(report["provenance"]["external_processes_started"])
            self.assertEqual(len(report["audit"]), 3)
            self.assertEqual([event["seq"] for event in report["audit"]], [1, 2, 3])
            self.assertEqual(report["audit"][0]["prev_hash"], "0" * 64)
            self.assertTrue(verify_report(report, FIXTURE_KEY))
            self.assertFalse(verify_report(report, FIXTURE_KEY + "-wrong"))
            self.assertTrue(Path(output).is_file())

    def test_audit_tamper_fails_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            report = build(str(Path(directory) / "report.json"), FIXTURE_KEY)
            report["audit"][1]["payload"]["count"] = 999
            self.assertFalse(verify_report(report, FIXTURE_KEY))


if __name__ == "__main__":
    unittest.main()

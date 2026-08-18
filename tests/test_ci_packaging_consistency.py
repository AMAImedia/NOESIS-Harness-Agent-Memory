import tempfile
import unittest
from pathlib import Path

from scripts.check_ci_packaging_consistency import check


class CIPackagingConsistencyTests(unittest.TestCase):
    def test_current_ci_and_runbook_are_consistent(self):
        report = check()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["ci"]["missing_markers"], [])
        self.assertEqual(report["runbook"]["missing_markers"], [])

    def test_missing_ci_marker_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / "docs").mkdir()
            (root / ".github" / "workflows" / "ci.yml").write_text("python scripts/verify_python314.py --json\n", encoding="utf-8")
            (root / "docs" / "NATIVE_PACKAGING_RUNBOOK_RU.md").write_text("Python 3.14.7\n", encoding="utf-8")
            report = check(str(root))
            self.assertEqual(report["status"], "failed")
            self.assertIn("python scripts/verify_portable_artifact.py", report["ci"]["missing_markers"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

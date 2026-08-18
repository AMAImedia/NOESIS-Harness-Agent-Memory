import tempfile
import unittest
from pathlib import Path

from scripts.check_release_metadata import audit


class ReleaseMetadataTests(unittest.TestCase):
    def test_current_release_metadata_and_provenance_pass(self):
        report = audit()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["findings"], [])
        self.assertEqual(set(report["provenance_names"]), set(report["expected_upstreams"]))

    def test_missing_required_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ("LICENSE", "README.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md", "pyproject.toml", "docs/README.md"):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("placeholder\n", encoding="utf-8")
            (root / "noesis_harness").mkdir()
            (root / "docs" / "third_party_provenance.json").write_text('{"upstreams": []}\n', encoding="utf-8")
            report = audit(str(root))
            self.assertEqual(report["status"], "failed")
            self.assertIn("failed_check:python_policy", report["findings"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

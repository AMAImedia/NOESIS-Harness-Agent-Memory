import tempfile
import unittest
from pathlib import Path

from scripts.check_markdown_links import audit as audit_links
from scripts.docs_security_audit import audit as audit_docs


class DocumentationAuditTests(unittest.TestCase):
    def test_project_docs_security_is_clean(self):
        report = audit_docs(".")
        self.assertTrue(report["clean"], report["findings"])
        self.assertEqual(report["high_count"], 0)
        self.assertEqual(report["medium_count"], 0)

    def test_project_links_are_clean_and_runtime_is_excluded(self):
        report = audit_links(".")
        self.assertTrue(report["clean"], report["findings"])
        self.assertNotIn("runtime", " ".join(item["source"] for item in report["findings"]))

    def test_missing_local_link_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("[missing](missing.md)\n", encoding="utf-8")
            report = audit_links(str(root))
            self.assertFalse(report["clean"])
            self.assertEqual(report["findings"][0]["rule"], "missing_local_target")


if __name__ == "__main__":
    unittest.main(verbosity=2)

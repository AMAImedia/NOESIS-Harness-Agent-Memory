from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from noesis_harness.skill_discovery import discover


class SkillDiscoveryTests(unittest.TestCase):
    def write_skill(self, root: Path, name: str, body: str) -> Path:
        path = root / name
        path.mkdir()
        file = path / "SKILL.md"
        file.write_text(body, encoding="utf-8")
        return file

    def test_valid_skill_is_discovered_with_digest_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_skill(root, "git-release", "---\nname: git-release\ndescription: Create safe releases\nlicense: MIT\n---\n# body\n")
            records = discover([str(root)])
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].status, "visible")
            self.assertEqual(records[0].name, "git-release")
            self.assertTrue(records[0].digest.startswith("sha256:"))

    def test_permission_policy_defaults_deny_and_last_matching_pattern_wins(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_skill(root, "internal-docs", "---\nname: internal-docs\ndescription: Internal documentation\n---\n")
            self.write_skill(root, "public-docs", "---\nname: public-docs\ndescription: Public documentation\n---\n")
            records = discover([str(root)], {"*": "deny", "public-*": "allow"})
            self.assertEqual([record.status for record in records], ["deny", "allow"])
            self.assertIn("permission", records[0].reason)

    def test_invalid_metadata_is_explicitly_denied(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_skill(root, "Bad Name", "---\nname: Bad Name\ndescription: invalid\n---\n")
            self.write_skill(root, "unknown-field", "---\nname: unknown-field\ndescription: invalid\nunsafe: yes\n---\n")
            records = discover([str(root)])
            self.assertEqual(len(records), 2)
            self.assertTrue(all(record.status == "deny" for record in records))
            self.assertTrue(all(record.reason for record in records))

    def test_file_root_is_supported_and_body_is_not_executed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = self.write_skill(root, "safe-skill", "---\nname: safe-skill\ndescription: Read only\n---\n__import__('os').system('false')\n")
            records = discover([str(file)])
            self.assertEqual(records[0].status, "visible")
            self.assertEqual(records[0].description, "Read only")


if __name__ == "__main__":
    unittest.main()

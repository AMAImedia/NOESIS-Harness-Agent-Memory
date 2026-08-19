import tempfile
import unittest
from pathlib import Path

from scripts.artifact_inventory import build_inventory, verify_inventory

KEY = "inventory-test-key-2026"


class ArtifactInventoryTests(unittest.TestCase):
    def test_inventory_is_deterministic_and_verifiable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "b.json"
            second = root / "a.json"
            first.write_text("b\n", encoding="utf-8")
            second.write_text("a\n", encoding="utf-8")
            one = build_inventory(root, [first, second], KEY, {"status": "passed"})
            two = build_inventory(root, [second, first], KEY, {"status": "passed"})
            self.assertEqual(one, two)
            self.assertEqual(verify_inventory(one, root, KEY)["status"], "passed")
            self.assertEqual([item["path"] for item in one["files"]], ["a.json", "b.json"])

    def test_tampered_file_and_manifest_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "artifact.json"
            target.write_text("original\n", encoding="utf-8")
            inventory = build_inventory(root, [target], KEY, {"status": "passed"})
            target.write_text("tampered\n", encoding="utf-8")
            self.assertEqual(verify_inventory(inventory, root, KEY)["reason"], "inventory_file_mismatch")
            target.write_text("original\n", encoding="utf-8")
            inventory["files"][0]["path"] = "../outside.json"
            self.assertEqual(verify_inventory(inventory, root, KEY)["reason"], "inventory_digest_mismatch")

    def test_missing_and_outside_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "artifact.json"
            target.write_text("data\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "inventory_file_invalid"):
                build_inventory(root, [root / "missing.json"], KEY, {})
            with self.assertRaisesRegex(ValueError, "inventory_file_invalid"):
                build_inventory(root, [Path(directory).parent / "outside.json"], KEY, {})


if __name__ == "__main__":
    unittest.main()

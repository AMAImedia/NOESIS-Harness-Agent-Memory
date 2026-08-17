from __future__ import annotations

import unittest

from scripts.verify_packaging_contract import audit


class PackagingContractTests(unittest.TestCase):
    def test_static_native_packaging_contract_is_complete(self):
        report = audit()
        self.assertEqual(report["status"], "passed")
        self.assertFalse(report["native_builds_executed"])
        self.assertEqual({item["target"] for item in report["manifests"]}, {"windows", "macos"})
        self.assertTrue(all(item["status"] == "passed" for item in report["manifests"]))


if __name__ == "__main__":
    unittest.main()

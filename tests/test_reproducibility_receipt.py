import unittest

from scripts.reproducibility_receipt import build_reproducibility_receipt, verify_reproducibility_receipt

KEY = "readiness-test-key-2026"


class ReproducibilityReceiptTests(unittest.TestCase):
    components = {"inventory_digest": "i" * 64, "aggregate_digest": "a" * 64, "chain_digest": "c" * 64}

    def test_timestamp_is_excluded_and_fingerprint_is_stable(self):
        first = build_reproducibility_receipt(**self.components, key=KEY, observed_at="2026-08-19T00:00:00Z")
        second = build_reproducibility_receipt(**self.components, key=KEY, observed_at="2026-08-20T00:00:00Z")
        self.assertEqual(first["receipt_digest"], second["receipt_digest"])
        self.assertEqual(first["signature"], second["signature"])
        self.assertEqual(verify_reproducibility_receipt(first, **self.components, key=KEY)["status"], "passed")

    def test_component_drift_and_tamper_are_rejected(self):
        receipt = build_reproducibility_receipt(**self.components, key=KEY)
        drifted = dict(receipt)
        drifted["chain_digest"] = "d" * 64
        self.assertEqual(verify_reproducibility_receipt(drifted, **self.components, key=KEY)["reason"], "reproducibility_digest_mismatch")
        self.assertEqual(verify_reproducibility_receipt(receipt, **{**self.components, "aggregate_digest": "b" * 64}, key=KEY)["reason"], "reproducibility_component_drift")


if __name__ == "__main__":
    unittest.main()

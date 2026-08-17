from __future__ import annotations

import unittest

from scripts.external_runner_contract import make_spec
from scripts.ingest_runner_result import ingest
from scripts.evaluate_signed_ab import evaluate


KEY = "local-test-evaluator-key-2026"


def evidence_for(system: str, revision: str, digest: str, model: str = "same-model"):
    spec = make_spec(system, revision, [system, "run"], digest, model_provider=model)
    result = {
        **spec,
        "execution": "completed",
        "status": "passed",
        "metrics": {
            "task_success": {"status": "observed", "value": 1.0},
            "latency_ms": {"status": "observed", "value": 10.0 if system == "hermes" else 12.0},
            "patch_correctness": {"status": "not_run", "reason": "fixture lane"},
        },
    }
    return ingest(spec, result, KEY)


class SignedABEvaluationTests(unittest.TestCase):
    def test_matching_fingerprint_allows_metric_comparison(self):
        report = evaluate((evidence_for("hermes", "h1", "a" * 64), evidence_for("opencode", "o1", "a" * 64)), KEY)
        self.assertTrue(report["comparable"])
        self.assertEqual(report["reason"], "protocol_fingerprint_match")
        self.assertTrue(report["metrics"]["latency_ms"]["comparable"])
        self.assertFalse(report["metrics"]["patch_correctness"]["comparable"])

    def test_mismatched_fingerprint_never_creates_comparison(self):
        report = evaluate((evidence_for("hermes", "h1", "a" * 64), evidence_for("opencode", "o1", "b" * 64)), KEY)
        self.assertFalse(report["comparable"])
        self.assertTrue(report["metrics"])
        self.assertTrue(all(item["comparable"] is False for item in report["metrics"].values()))

    def test_not_run_records_cannot_establish_external_comparison(self):
        first = evidence_for("hermes", "h1", "a" * 64)
        second = evidence_for("opencode", "o1", "a" * 64)
        first["status"] = "not_run"
        second["status"] = "not_run"
        from scripts.ingest_runner_result import signature
        first["signature"] = signature({name: value for name, value in first.items() if name != "signature"}, KEY)
        second["signature"] = signature({name: value for name, value in second.items() if name != "signature"}, KEY)
        report = evaluate((first, second), KEY)
        self.assertFalse(report["comparable"])
        self.assertEqual(report["reason"], "not_run evidence cannot establish an external comparison")

    def test_tampered_signature_is_not_comparable(self):
        first = evidence_for("hermes", "h1", "a" * 64)
        second = dict(evidence_for("opencode", "o1", "a" * 64))
        second["signature"] = "hmac-sha256:" + "0" * 64
        report = evaluate((first, second), KEY)
        self.assertFalse(report["comparable"])
        self.assertFalse(report["records"][1]["signature_valid"])


if __name__ == "__main__":
    unittest.main()

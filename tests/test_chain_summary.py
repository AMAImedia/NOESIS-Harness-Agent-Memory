import json
import tempfile
import unittest
from pathlib import Path

from scripts.chain_summary import verify_chain_summary
from scripts.run_operator_evidence_pipeline import run_pipeline

from tests.test_external_evidence_readiness import evidence_for, manifest

KEY = "readiness-test-key-2026"


class ChainSummaryTests(unittest.TestCase):
    def write(self, path, value):
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

    def build(self, root):
        evidence = [evidence_for("hermes", "h1"), evidence_for("opencode", "o1"), evidence_for("deepseek_harness", "d1")]
        manifest_path = root / "manifest.json"
        self.write(manifest_path, manifest(protocol_fingerprint=evidence[0]["protocol_fingerprint"]))
        paths = []
        for index, record in enumerate(evidence):
            path = root / ("evidence-%d.json" % index)
            self.write(path, record)
            paths.append(str(path))
        artifact_root = root / "artifacts"
        result = run_pipeline(str(manifest_path), paths, KEY, str(artifact_root))
        return artifact_root, result

    def test_chain_summary_is_emitted_and_verifiable(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, result = self.build(Path(directory))
            summary = json.loads((artifact_root / "chain-summary.json").read_text(encoding="utf-8"))
            inventory = json.loads((artifact_root / "artifact-manifest.json").read_text(encoding="utf-8"))
            aggregate = json.loads((artifact_root / "signed-external-evidence-aggregate.json").read_text(encoding="utf-8"))
            verification = json.loads((artifact_root / "verification-result.json").read_text(encoding="utf-8"))
            checked = verify_chain_summary(summary, inventory, aggregate, verification, KEY)
            self.assertEqual(checked["status"], "passed")
            self.assertEqual(result["chain_summary_digest"], summary["chain_digest"])

    def test_chain_summary_component_drift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact_root, _ = self.build(Path(directory))
            summary = json.loads((artifact_root / "chain-summary.json").read_text(encoding="utf-8"))
            inventory = json.loads((artifact_root / "artifact-manifest.json").read_text(encoding="utf-8"))
            aggregate = json.loads((artifact_root / "signed-external-evidence-aggregate.json").read_text(encoding="utf-8"))
            verification = json.loads((artifact_root / "verification-result.json").read_text(encoding="utf-8"))
            aggregate["aggregate_digest"] = "0" * 64
            self.assertEqual(verify_chain_summary(summary, inventory, aggregate, verification, KEY)["reason"], "chain_summary_aggregate_drift")
            summary["signature"] = "0" * 64
            self.assertEqual(verify_chain_summary(summary, inventory, json.loads((artifact_root / "signed-external-evidence-aggregate.json").read_text(encoding="utf-8")), verification, KEY)["reason"], "chain_summary_signature_invalid")


if __name__ == "__main__":
    unittest.main()

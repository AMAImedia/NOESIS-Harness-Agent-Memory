from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_local_signed_ab_fixture import run


class LocalSignedABFixtureTests(unittest.TestCase):
    def test_fixture_lane_is_reproducible_and_comparable(self):
        with tempfile.TemporaryDirectory() as directory:
            first_path = str(Path(directory) / "first.json")
            second_path = str(Path(directory) / "second.json")
            first = run(first_path)
            second = run(second_path)
            self.assertTrue(first["simulation_only"])
            self.assertFalse(first["external_processes_started"])
            self.assertTrue(first["evaluation"]["comparable"])
            self.assertEqual(first["evaluation"]["protocol_fingerprints"], second["evaluation"]["protocol_fingerprints"])
            self.assertEqual(first["task_manifest_sha256"], second["task_manifest_sha256"])
            self.assertEqual(first["evaluation"]["metrics"]["latency_ms"]["values"], second["evaluation"]["metrics"]["latency_ms"]["values"])
            decoded = json.loads(Path(first_path).read_text(encoding="utf-8"))
            self.assertEqual(decoded["schema_version"], "noesis.local-signed-ab-fixture.v1")
            self.assertEqual(len(decoded["evidence"]), 2)
            self.assertEqual({item["system"] for item in decoded["evidence"]}, {"hermes", "opencode"})


if __name__ == "__main__":
    unittest.main()

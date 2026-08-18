from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_portable_artifact import build


class PortableArtifactTests(unittest.TestCase):
    def test_artifact_contains_manifest_and_deterministic_spdx_sbom(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            (root / "README.md").write_text("safe project\n", encoding="utf-8")
            (root / "main.py").write_text("print('ok')\n", encoding="utf-8")
            (root / ".env").write_text("TOKEN=must-not-ship\n", encoding="utf-8")
            (root / "models").mkdir()
            (root / "models" / "weights.bin").write_bytes(b"weights")
            output = Path(directory) / "artifact.zip"
            result = build(str(root), str(output))
            with zipfile.ZipFile(output) as archive:
                manifest = json.loads(archive.read("PORTABLE_MANIFEST.json"))
                sbom = json.loads(archive.read("PORTABLE_SBOM.spdx.json"))
                names = set(archive.namelist())
            self.assertEqual(manifest["runtime"], "python-3.14-only")
            self.assertEqual(manifest["sbom"]["format"], "SPDX-2.3")
            self.assertEqual(sbom["spdxVersion"], "SPDX-2.3")
            self.assertEqual(len(sbom["files"]), result["file_count"])
            self.assertIn("README.md", names)
            self.assertNotIn(".env", names)
            self.assertNotIn("models/weights.bin", names)
            listed = {entry["path"] for entry in manifest["files"]}
            self.assertEqual(listed, {"README.md", "main.py"})
            self.assertEqual({entry["fileName"] for entry in sbom["files"]}, listed)

    def test_artifact_sha256_is_stable_for_same_file_inventory(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            (root / "a.txt").write_text("A\n", encoding="utf-8")
            first_path = Path(directory) / "one.zip"
            second_path = Path(directory) / "two.zip"
            build(str(root), str(first_path))
            build(str(root), str(second_path))
            first = hashlib.sha256(first_path.read_bytes()).hexdigest()
            second = hashlib.sha256(second_path.read_bytes()).hexdigest()
            self.assertEqual(first, second)

    def test_sbom_namespace_is_stable_for_same_file_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            (root / "a.txt").write_text("A\n", encoding="utf-8")
            first = build(str(root), str(Path(directory) / "one.zip"))
            second = build(str(root), str(Path(directory) / "two.zip"))
            self.assertEqual(first["sbom"]["documentNamespace"], second["sbom"]["documentNamespace"])


if __name__ == "__main__":
    unittest.main()

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from scripts.build_portable_artifact import build
from scripts.verify_portable_artifact import verify


class PortableArtifactVerifierTests(unittest.TestCase):
    def make_artifact(self, root: Path, output: Path) -> None:
        root.mkdir()
        (root / "README.md").write_text("safe\n", encoding="utf-8")
        (root / "main.py").write_text("print('safe')\n", encoding="utf-8")
        build(str(root), str(output))

    def test_valid_manifest_and_spdx_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            artifact = Path(directory) / "artifact.zip"
            self.make_artifact(root, artifact)
            report = verify(str(artifact))
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["file_count"], 2)

    def test_tampered_payload_fails_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            artifact = Path(directory) / "artifact.zip"
            self.make_artifact(root, artifact)
            tampered = Path(directory) / "tampered.zip"
            with zipfile.ZipFile(artifact) as source, zipfile.ZipFile(tampered, "w") as target:
                for item in source.infolist():
                    data = source.read(item.filename)
                    if item.filename == "main.py":
                        data = b"tampered\n"
                    target.writestr(item, data)
            report = verify(str(tampered))
            self.assertEqual(report["status"], "failed")
            self.assertIn("sha256:main.py", report["errors"])

    def test_unexpected_archive_file_fails_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            artifact = Path(directory) / "artifact.zip"
            self.make_artifact(root, artifact)
            extra = Path(directory) / "extra.zip"
            with zipfile.ZipFile(artifact) as source, zipfile.ZipFile(extra, "w") as target:
                for item in source.infolist():
                    target.writestr(item, source.read(item.filename))
                target.writestr("unexpected.bin", b"unexpected")
            report = verify(str(extra))
            self.assertEqual(report["status"], "failed")
            self.assertIn("archive_manifest_coverage", report["errors"])

    def test_manifest_path_traversal_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            artifact = Path(directory) / "artifact.zip"
            self.make_artifact(root, artifact)
            tampered = Path(directory) / "traversal.zip"
            with zipfile.ZipFile(artifact) as source, zipfile.ZipFile(tampered, "w") as target:
                for item in source.infolist():
                    data = source.read(item.filename)
                    if item.filename == "PORTABLE_MANIFEST.json":
                        manifest = __import__("json").loads(data)
                        manifest["files"][0]["path"] = "../escape.txt"
                        data = (__import__("json").dumps(manifest)).encode("utf-8")
                    target.writestr(item, data)
            report = verify(str(tampered))
            self.assertEqual(report["status"], "failed")
            self.assertIn("unsafe_path:../escape.txt", report["errors"])

    def test_missing_metadata_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "missing.zip"
            with zipfile.ZipFile(artifact, "w") as archive:
                archive.writestr("main.py", b"safe")
            report = verify(str(artifact))
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["errors"], ["metadata_missing"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

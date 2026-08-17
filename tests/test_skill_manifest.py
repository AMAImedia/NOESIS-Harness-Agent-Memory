import json
import os
import tempfile
import unittest
from pathlib import Path

from noesis_harness.skill_manifest import SkillManifest, SkillManifestError, digest_files


class SkillManifestTests(unittest.TestCase):
    def manifest(self, **overrides):
        values = {
            "skill_id": "safe-summarizer",
            "name": "Safe Summarizer",
            "version": "1.0.0",
            "digest": "sha256:" + "a" * 64,
            "capabilities": ("models.read",),
            "platforms": ("windows", "macos"),
            "provenance": {"source": "AMAImedia/NOESIS-Harness-Agent-Memory", "license": "internal"},
            "entrypoint": "skill.json",
        }
        values.update(overrides)
        return SkillManifest(**values)

    def test_canonical_round_trip(self):
        manifest = self.manifest()
        decoded = SkillManifest.from_json(manifest.to_json())
        self.assertEqual(decoded, manifest)
        self.assertTrue(manifest.to_json().endswith("\n"))

    def test_digest_is_stable_and_ordered(self):
        with tempfile.TemporaryDirectory() as root:
            Path(root, "b.txt").write_text("B", encoding="utf-8")
            Path(root, "a.txt").write_text("A", encoding="utf-8")
            first = digest_files(root)
            second = digest_files(root)
            self.assertEqual(first, second)
            self.assertTrue(first.startswith("sha256:"))

    def test_unknown_fields_and_missing_fields_fail_closed(self):
        data = json.loads(self.manifest().to_json())
        data["unexpected"] = True
        with self.assertRaises(SkillManifestError):
            SkillManifest.from_json(json.dumps(data))
        del data["unexpected"]
        del data["digest"]
        with self.assertRaises(SkillManifestError):
            SkillManifest.from_json(json.dumps(data))

    def test_unsafe_paths_platforms_capabilities_and_provenance_fail(self):
        with self.assertRaises(SkillManifestError):
            self.manifest(entrypoint="../run.py")
        with self.assertRaises(SkillManifestError):
            self.manifest(platforms=("android",))
        with self.assertRaises(SkillManifestError):
            self.manifest(capabilities=("shell.exec",))
        with self.assertRaises(SkillManifestError):
            self.manifest(provenance={"source": "x", "api_key": "secret"})

    def test_digest_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root, "target.txt")
            target.write_text("safe", encoding="utf-8")
            link = Path(root, "link.txt")
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            with self.assertRaises(SkillManifestError):
                digest_files(root)

    def test_manifest_filename_is_enforced(self):
        with tempfile.TemporaryDirectory() as root:
            wrong = Path(root, "manifest.json")
            wrong.write_text(self.manifest().to_json(), encoding="utf-8")
            with self.assertRaises(SkillManifestError):
                SkillManifest.from_file(str(wrong))


if __name__ == "__main__":
    unittest.main()

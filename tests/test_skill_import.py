import json
import tempfile
import unittest
from pathlib import Path

from noesis_harness.skill_import import SafeSkillImport
from noesis_harness.skill_manifest import SkillManifest, digest_files


class SafeSkillImportTests(unittest.TestCase):
    def make_bundle(self, root, content="safe"):
        Path(root, "skill.txt").write_text(content, encoding="utf-8")
        digest = digest_files(root)
        manifest = SkillManifest(
            skill_id="safe-skill",
            name="Safe Skill",
            version="1.0.0",
            digest=digest,
            capabilities=("models.read",),
            platforms=("any",),
            provenance={"source": "local-test"},
        )
        Path(root, ".noesisskill").write_text(manifest.to_json(), encoding="utf-8")

    def test_stage_then_approve_with_passing_hook(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as staging:
            self.make_bundle(root)
            pipeline = SafeSkillImport(staging)
            scanned = pipeline.scan(root)
            self.assertEqual(scanned.status, "scanned")
            staged = pipeline.stage(root)
            self.assertEqual(staged.status, "staged")
            approved = pipeline.approve(staged, lambda path: Path(path, "skill.txt").read_text(encoding="utf-8") == "safe")
            self.assertEqual(approved.status, "approved")
            self.assertTrue(Path(approved.staging_path, ".approved").is_file())

    def test_failed_test_hook_never_approves(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as staging:
            self.make_bundle(root)
            staged = SafeSkillImport(staging).stage(root)
            result = SafeSkillImport(staging).approve(staged, lambda _path: False)
            self.assertEqual(result.status, "rejected")
            self.assertEqual(result.reason, "test_hook_failed")

    def test_missing_manifest_and_digest_mismatch_reject(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as staging:
            Path(root, "skill.txt").write_text("safe", encoding="utf-8")
            pipeline = SafeSkillImport(staging)
            self.assertEqual(pipeline.scan(root).reason, "manifest_missing")
            self.make_bundle(root)
            Path(root, "skill.txt").write_text("tampered", encoding="utf-8")
            self.assertEqual(pipeline.scan(root).reason, "digest_mismatch")

    def test_limits_and_stage_required_fail_soft(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as staging:
            self.make_bundle(root, content="0123456789")
            small = SafeSkillImport(staging, max_bytes=1)
            self.assertEqual(small.scan(root).reason, "byte_limit_exceeded")
            result = SafeSkillImport(staging).approve(small.scan(root))
            self.assertEqual(result.reason, "stage_required")

    def test_symlink_is_rejected_when_supported(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as staging:
            self.make_bundle(root)
            target = Path(root, "skill.txt")
            link = Path(root, "link.txt")
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation unavailable")
            self.assertEqual(SafeSkillImport(staging).scan(root).reason, "symlink_detected")


if __name__ == "__main__":
    unittest.main()

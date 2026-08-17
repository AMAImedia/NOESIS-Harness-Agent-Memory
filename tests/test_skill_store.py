import tempfile
import unittest
from pathlib import Path

from noesis_harness.skill_import import SafeSkillImport
from noesis_harness.skill_manifest import SkillManifest, digest_files
from noesis_harness.skill_store import SkillStore, SkillStoreError


class SkillStoreTests(unittest.TestCase):
    def make_bundle(self, root, version, content):
        Path(root, "skill.txt").write_text(content, encoding="utf-8")
        digest = digest_files(root)
        manifest = SkillManifest(
            skill_id="rollback-skill",
            name="Rollback Skill",
            version=version,
            digest=digest,
            capabilities=("models.read",),
            platforms=("any",),
            provenance={"source": "local-test"},
        )
        Path(root, ".noesisskill").write_text(manifest.to_json(), encoding="utf-8")

    def approved(self, bundle, staging):
        pipeline = SafeSkillImport(staging)
        staged = pipeline.stage(bundle)
        self.assertEqual(staged.status, "staged")
        approved = pipeline.approve(staged, lambda path: Path(path, "skill.txt").is_file())
        self.assertEqual(approved.status, "approved")
        return approved

    def test_install_upgrade_and_rollback_keep_previous_version(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as staging, tempfile.TemporaryDirectory() as store_root:
            first = Path(root, "v1")
            second = Path(root, "v2")
            first.mkdir()
            second.mkdir()
            self.make_bundle(str(first), "1.0.0", "one")
            self.make_bundle(str(second), "2.0.0", "two")
            store = SkillStore(store_root)
            store.install_approved(self.approved(str(first), staging))
            self.assertEqual(store.active("rollback-skill")["version"], "1.0.0")
            store.install_approved(self.approved(str(second), staging))
            self.assertEqual(store.active("rollback-skill")["version"], "2.0.0")
            restored = store.rollback("rollback-skill")
            self.assertEqual(restored["version"], "1.0.0")
            self.assertTrue((Path(store_root) / "skills" / "rollback-skill" / "versions" / "2.0.0" / "skill.txt").is_file())

    def test_failed_install_leaves_active_version_unchanged_and_audited(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as staging, tempfile.TemporaryDirectory() as store_root:
            first = Path(root, "v1")
            first.mkdir()
            self.make_bundle(str(first), "1.0.0", "one")
            store = SkillStore(store_root)
            store.install_approved(self.approved(str(first), staging))
            invalid = Path(root, "invalid")
            invalid.mkdir()
            self.make_bundle(str(invalid), "2.0.0", "two")
            staged = SafeSkillImport(staging).stage(str(invalid))
            self.assertEqual(staged.status, "staged")
            approved = SafeSkillImport(staging).approve(staged, lambda _path: False)
            self.assertEqual(approved.status, "rejected")
            with self.assertRaises(SkillStoreError):
                store.install_approved(approved)
            self.assertEqual(store.active("rollback-skill")["version"], "1.0.0")
            events = store.audit_events()
            self.assertTrue(events)
            self.assertEqual(events[-1]["type"], "skill_install")
            self.assertEqual(events[-1]["status"], "rolled_back")

    def test_rollback_without_previous_version_fails_closed(self):
        with tempfile.TemporaryDirectory() as store_root:
            with self.assertRaises(SkillStoreError):
                SkillStore(store_root).rollback("missing")


if __name__ == "__main__":
    unittest.main()

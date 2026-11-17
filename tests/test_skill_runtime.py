import json
import sys
import tempfile
import unittest
from pathlib import Path

from noesis_harness.child_execution import ChildExecutionRuntime
from noesis_harness.gatekeeper import CapabilityRequest, Gatekeeper
from noesis_harness.skill_import import SafeSkillImport
from noesis_harness.skill_manifest import SkillManifest, digest_files
from noesis_harness.skill_runtime import ExecutableSkillRuntime
from noesis_harness.skill_store import SkillStore


class SkillRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.source = root / "source"
        self.source.mkdir()
        (self.source / "run.py").write_text("print('skill-child-ok')\n", encoding="utf-8")
        manifest = SkillManifest("demo-skill", "Demo", "1.0.0", digest_files(str(self.source)), ("skill.execute",), ("any",), {"source": "local-test"}, "run.py")
        (self.source / ".noesisskill").write_text(manifest.to_json(), encoding="utf-8")
        importer = SafeSkillImport(str(root / "staging"))
        assessment = importer.approve(importer.stage(str(self.source)), test_hook=lambda _: True)
        self.store = SkillStore(str(root / "store"))
        self.store.install_approved(assessment)
        self.gate = Gatekeeper(str(root / "gate.jsonl"))
        self.child = ChildExecutionRuntime(self.gate)
        self.runtime = ExecutableSkillRuntime(self.store, self.child, self.gate, require_hardened_sandbox=False)

    def tearDown(self):
        self.tmp.cleanup()

    def _gate(self, target="demo-skill"):
        request = CapabilityRequest("s", "t", "agent", "skill.execute", "run_skill", target, "write", {"skill": target})
        decision = self.gate.prepare(request)
        self.gate.approve(decision.request_id)
        self.gate.commit(decision.request_id)
        return decision.request_id

    def test_hardened_runtime_requires_promotion_receipt(self):
        strict = ExecutableSkillRuntime(self.store, self.child, self.gate)
        with self.assertRaisesRegex(ValueError, "promotion_receipt_required"):
            strict._installed_root("demo-skill")

    def test_strict_manifest_execution_requires_hardened_backend(self):
        strict = ExecutableSkillRuntime(self.store, self.child, self.gate)
        result = strict.run("demo-skill", self._gate())
        self.assertEqual(result.status, "denied")
        self.assertEqual(result.reason, "skill_requires_hardened_sandbox")

    def test_verified_skill_runs_in_child_process(self):
        result = self.runtime.run("demo-skill", self._gate())
        self.assertEqual(result.status, "completed")
        self.assertIn("skill-child-ok", result.stdout)

    def test_uncommitted_or_wrong_target_is_denied(self):
        request = CapabilityRequest("s", "t", "agent", "skill.execute", "run_skill", "demo-skill", "write", {})
        decision = self.gate.prepare(request)
        denied = self.runtime.run("demo-skill", decision.request_id)
        self.assertEqual(denied.reason, "gatekeeper_commit_required")
        wrong = self.runtime.run("other-skill", self._gate())
        self.assertEqual(wrong.reason, "skill_capability_target_mismatch")

    def test_tampered_installed_version_is_denied(self):
        active = self.store.active("demo-skill")
        installed = self.store.skills_root / "demo-skill" / "versions" / active["version"]
        (installed / "run.py").write_text("print('tampered')\n", encoding="utf-8")
        result = self.runtime.run("demo-skill", self._gate())
        self.assertEqual(result.status, "denied")
        self.assertEqual(result.reason, "skill_digest_mismatch")


if __name__ == "__main__":
    unittest.main()

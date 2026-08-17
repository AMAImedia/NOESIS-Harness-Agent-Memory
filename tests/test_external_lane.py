from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.external_runner_contract import make_spec
from scripts.run_external_lane import main, plan


class ExternalLaneTests(unittest.TestCase):
    def test_dry_run_plan_never_starts_process(self):
        with tempfile.TemporaryDirectory() as directory:
            spec = make_spec("hermes", "pinned-h1", [sys.executable, "-c", "raise SystemExit(9)"], "a" * 64)
            report = plan(spec, directory)
            self.assertEqual(report["execution"], "not_started")
            self.assertTrue(report["approval_required"])
            self.assertEqual(report["reason"], "dry_run_only")

    def test_cli_execute_requires_approval_and_writes_not_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec_path = root / "spec.json"
            output = root / "plan.json"
            spec_path.write_text(json.dumps(make_spec("opencode", "pinned-o1", [sys.executable, "-c", "print('x')"], "b" * 64)), encoding="utf-8")
            code = main(["--spec", str(spec_path), "--workspace", str(root), "--output", str(output), "--execute"])
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(code, 2)
            self.assertEqual(report["execution"], "denied")
            self.assertEqual(report["status"], "not_run")

    def test_cli_approved_controlled_execution_is_structured(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec_path = root / "spec.json"
            output = root / "result.json"
            spec_path.write_text(json.dumps(make_spec("hermes", "pinned-h1", [sys.executable, "-c", "print('fixture-run')"], "c" * 64)), encoding="utf-8")
            code = main(["--spec", str(spec_path), "--workspace", str(root), "--output", str(output), "--execute", "--approve"])
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(code, 0)
            self.assertEqual(report["execution"], "started")
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["stdout"].strip(), "fixture-run")


if __name__ == "__main__":
    unittest.main()

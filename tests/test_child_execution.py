import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from noesis_harness.child_execution import ChildExecutionRuntime, ExecutionRequest
from noesis_harness.gatekeeper import CapabilityRequest, Gatekeeper
from noesis_harness.sandbox_bwrap import BubblewrapBackend


class ChildExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.workspace = root / "workspace"
        self.workspace.mkdir()
        (self.workspace / "ok.py").write_text("print('child-ok')\n", encoding="utf-8")
        (self.workspace / "slow.py").write_text("import time\ntime.sleep(2)\n", encoding="utf-8")
        (self.workspace / "leak.py").write_text("print('token=hf_TEST_SECRET_VALUE_123456')\n", encoding="utf-8")
        (self.workspace / "noisy.py").write_text("print('x' * 1000)\n", encoding="utf-8")
        try:
            (self.workspace / "link.py").symlink_to(self.workspace / "ok.py")
        except (OSError, NotImplementedError):
            self.link_supported = False
        else:
            self.link_supported = True
        self.gate = Gatekeeper(str(root / "gate.jsonl"))
        self.runtime = ChildExecutionRuntime(self.gate)

    def tearDown(self):
        self.tmp.cleanup()

    def _approved_request(self, capability="skill.execute", action="run_skill", target="ok.py"):
        gate_request = CapabilityRequest("s", "t", "a", capability, action, target, "write", {"target": target})
        decision = self.gate.prepare(gate_request)
        self.gate.approve(decision.request_id)
        self.gate.commit(decision.request_id)
        return decision.request_id

    def _request(self, request_id, script="ok.py", timeout=2.0, network=False):
        return ExecutionRequest(request_id, (sys.executable, script), str(self.workspace), (Path(sys.executable).name,), timeout_seconds=timeout, network=network)

    def test_requires_gatekeeper_commit(self):
        gate_request = CapabilityRequest("s", "t", "a", "skill.execute", "run_skill", "ok.py", "write", {})
        decision = self.gate.prepare(gate_request)
        result = self.runtime.run(self._request(decision.request_id))
        self.assertEqual(result.status, "denied")
        self.assertEqual(result.reason, "gatekeeper_commit_required")

    def test_runs_allowlisted_file_without_shell(self):
        request_id = self._approved_request()
        result = self.runtime.run(self._request(request_id))
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.returncode, 0)
        self.assertIn("child-ok", result.stdout)
        self.assertFalse(result.sandboxed)

    def test_network_and_inline_code_are_denied(self):
        request_id = self._approved_request()
        result = self.runtime.run(self._request(request_id, network=True))
        self.assertEqual(result.status, "denied")
        self.assertIn("network_isolation", result.reason)
        bad = ExecutionRequest(request_id, (sys.executable, "-c", "print('bad')"), str(self.workspace), (Path(sys.executable).name,))
        self.assertEqual(self.runtime.run(bad).status, "denied")

    def test_timeout_terminates_child(self):
        request_id = self._approved_request(target="slow.py")
        result = self.runtime.run(self._request(request_id, script="slow.py", timeout=0.1))
        self.assertEqual(result.status, "timeout")
        self.assertEqual(result.reason, "timeout_budget_exceeded")

    def test_environment_allowlist_is_fail_closed(self):
        request_id = self._approved_request()
        request = ExecutionRequest(request_id, (sys.executable, "ok.py"), str(self.workspace), (Path(sys.executable).name,), environment={"NOESIS_SECRET": "blocked"})
        result = self.runtime.run(request)
        self.assertEqual(result.status, "denied")
        self.assertIn("environment_key_not_allowlisted", result.reason)

    def test_symlink_entrypoint_is_denied(self):
        if not self.link_supported:
            self.skipTest("symlink unsupported on this host")
        request_id = self._approved_request(target="link.py")
        result = self.runtime.run(self._request(request_id, script="link.py"))
        self.assertEqual(result.status, "denied")
        self.assertEqual(result.reason, "entrypoint_missing_or_symlink")

    def test_output_budget_is_bounded(self):
        request_id = self._approved_request(target="noisy.py")
        request = ExecutionRequest(request_id, (sys.executable, "noisy.py"), str(self.workspace), (Path(sys.executable).name,), output_limit=64)
        result = self.runtime.run(request)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "output_budget_exceeded")
        self.assertLessEqual(len(result.stdout.encode("utf-8")), 64)

    def test_credential_like_output_is_redacted_and_blocked(self):
        request_id = self._approved_request(target="leak.py")
        result = self.runtime.run(self._request(request_id, script="leak.py"))
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.reason, "credential_like_output_blocked")
        self.assertNotIn("hf_TEST_SECRET_VALUE_123456", result.stdout)
        self.assertIn("[REDACTED_CREDENTIAL]", result.stdout)

    def test_executable_allowlist_and_workspace_boundary(self):
        request_id = self._approved_request()
        bad_exe = ExecutionRequest(request_id, ("not-allowlisted", "ok.py"), str(self.workspace), (Path(sys.executable).name,))
        self.assertEqual(self.runtime.run(bad_exe).reason, "executable_not_allowlisted")
        traversal = ExecutionRequest(request_id, (sys.executable, "../ok.py"), str(self.workspace), (Path(sys.executable).name,))
        self.assertEqual(self.runtime.run(traversal).reason, "entrypoint_outside_workspace")

    def test_bubblewrap_backend_is_explicitly_sandboxed(self):
        backend = BubblewrapBackend()
        if not backend.available:
            self.skipTest("bubblewrap unavailable")
        request_id = self._approved_request()
        runtime = ChildExecutionRuntime(self.gate, sandbox_backend=backend)
        python3 = shutil.which("python3") or "/usr/bin/python3"
        request = ExecutionRequest(request_id, (python3, "ok.py"), str(self.workspace), (Path(python3).name,))
        result = runtime.run(request)
        self.assertEqual(result.status, "completed")
        self.assertTrue(result.sandboxed)
        self.assertIn("child-ok", result.stdout)

    def test_unavailable_backend_fails_closed(self):
        class Unavailable:
            available = False
            backend_id = "test-unavailable"
            host_platform = "test"
        request_id = self._approved_request()
        runtime = ChildExecutionRuntime(self.gate, sandbox_backend=Unavailable())
        result = runtime.run(self._request(request_id))
        self.assertEqual(result.status, "denied")
        self.assertEqual(result.reason, "sandbox_backend_unavailable")
        self.assertFalse(result.sandboxed)


if __name__ == "__main__":
    unittest.main()

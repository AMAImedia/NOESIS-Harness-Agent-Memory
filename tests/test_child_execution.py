import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from noesis_harness.child_execution import ChildExecutionRuntime, ExecutionRequest
from noesis_harness.execution_assurance import ExecutionReceiptStore, ExecutionRecoveryStore
from noesis_harness.gatekeeper import CapabilityRequest, Gatekeeper
from noesis_harness.sandbox_bwrap import BubblewrapBackend
from noesis_harness.skill_manifest import SkillManifest

# Roots that BubblewrapBackend.command mounts read-only into the child. Keep in
# sync with the --ro-bind lines in noesis_harness/sandbox_bwrap.py.
_SANDBOX_READ_ONLY_ROOTS = ("/usr", "/bin", "/lib", "/lib64")

# bwrap prefixes every diagnostic of its own with "bwrap:". Only such a line
# proves that the sandbox could not start the child at all. A child that did run
# and then failed can also print "No such file or directory" or "Permission
# denied" in its own traceback, and that must surface as a failing assertion,
# never as a skip -- which is why a bare substring match is not used here.
_SANDBOX_DIAGNOSTIC_PREFIX = "bwrap:"


def _inside_sandbox_roots(path: Path) -> bool:
    for root in _SANDBOX_READ_ONLY_ROOTS:
        root_path = Path(root)
        if path == root_path or root_path in path.parents:
            return True
    return False


def _sandbox_interpreter() -> str:
    """Return the Python interpreter that the bubblewrap bind set can exec.

    ``BubblewrapBackend.command`` mounts exactly ``/usr``, ``/bin``, ``/lib``,
    ``/lib64``, ``/etc``, ``/proc``, ``/dev``, a tmpfs ``/tmp`` and the
    workspace, and it sets ``PATH=/usr/bin:/bin`` for the child. An interpreter
    outside those roots simply does not exist from the child's point of view.

    That is not hypothetical: GitHub's hosted Ubuntu runner exposes Python at
    ``/opt/hostedtoolcache/Python/<version>/x64/bin/python3``, which is what
    ``shutil.which("python3")`` returns there. Using it as ``argv[0]`` made
    bwrap fail to exec the child, so the runtime honestly reported
    ``status="failed"`` while namespaces were working. On hosts where Python
    lives in ``/usr/bin`` the same test passed, which hid the mistake.

    Candidates, each checked by real path so a symlink cannot smuggle in an
    unbindable target:

    1. ``sys.executable`` -- the interpreter running these tests, when its real
       path is under a bound root;
    2. ``/usr/bin/python3`` -- the system interpreter, when its real path is
       under a bound root;
    3. ``shutil.which("python3")`` -- last resort. ``_bubblewrap_skip_reason``
       then decides whether it is usable, so the test skips with
       "cannot execute ... inside the sandbox" instead of asserting a success
       it never observed.
    """
    candidates = (sys.executable, "/usr/bin/python3", shutil.which("python3") or "")
    for candidate in candidates:
        if not candidate:
            continue
        resolved = Path(os.path.realpath(candidate))
        if resolved.is_file() and os.access(str(resolved), os.X_OK) and _inside_sandbox_roots(resolved):
            return str(resolved)
    return shutil.which("python3") or "/usr/bin/python3"


def _bubblewrap_skip_reason(backend: BubblewrapBackend, workspace: Path, argv) -> str:
    """Return why this host cannot run ``argv`` under bubblewrap, or "".

    ``BubblewrapBackend.available`` only proves the binary exists. A host can
    have bwrap installed and still refuse to create a user namespace, which is
    what happens when the kernel restricts unprivileged user namespaces (for
    example ``kernel.apparmor_restrict_unprivileged_userns=1`` on newer Ubuntu,
    or a seccomp profile that blocks ``unshare``). A second way to fail is an
    interpreter the bind set does not cover. Both are environment limits, and
    both turn into a failing assertion about the sandbox unless they are probed.

    ``argv`` is the exact command line the caller is about to hand to the
    runtime, so the probe exercises the same interpreter and the same script,
    through the backend's own command builder, in the same workspace with the
    same mounts. That is strictly stronger than a ``python -c`` exec probe: it
    also proves the interpreter can open the script from the bound workspace.

    A skip is returned only when the failure is an exec/namespace failure
    reported by bwrap itself. If the child ran and the script exited non-zero,
    this returns "" on purpose so the test executes and fails with evidence
    instead of hiding a real defect behind a skip.
    """
    if shutil.which(backend.executable or "bwrap") is None:
        return "bubblewrap not installed on this host"
    if not backend.available:
        return "bubblewrap unavailable on this host"
    try:
        command = backend.command(tuple(argv), workspace)
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except Exception as exc:
        lines = str(exc).strip().splitlines()
        return "bubblewrap cannot start a sandbox for %s on this host: %s: %s" % (
            argv[0],
            type(exc).__name__,
            lines[-1] if lines else "no detail",
        )
    if completed.returncode == 0:
        return ""
    lines = [line for line in (completed.stderr or completed.stdout or "").strip().splitlines() if line.strip()]
    last_line = lines[-1] if lines else "exit %s" % completed.returncode
    if last_line.startswith(_SANDBOX_DIAGNOSTIC_PREFIX):
        return "bubblewrap cannot execute %s inside the sandbox on this host: %s" % (argv[0], last_line)
    return ""


class ChildExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.workspace = root / "workspace"
        self.workspace.mkdir()
        (self.workspace / "ok.py").write_text("print('child-ok')\n", encoding="utf-8")
        (self.workspace / "slow.py").write_text("import time\ntime.sleep(2)\n", encoding="utf-8")
        (self.workspace / "tree.py").write_text("import subprocess, sys, time\nsubprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\ntime.sleep(30)\n", encoding="utf-8")
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

    def test_manifest_capability_grant_is_required(self):
        request_id = self._approved_request()
        manifest = SkillManifest("demo-skill", "Demo", "1.0.0", "sha256:" + "0" * 64, ("skill.execute",), ("linux",), {"source": "test"}, "ok.py")
        request = ExecutionRequest(request_id, (sys.executable, "ok.py"), str(self.workspace), (Path(sys.executable).name,), skill_id="demo-skill", manifest=manifest)
        result = self.runtime.run(request)
        self.assertEqual(result.status, "denied")
        self.assertEqual(result.reason, "manifest_capability_grant_missing")

    def test_manifest_requires_hardened_backend_even_with_grant(self):
        request_id = self._approved_request()
        manifest = SkillManifest("demo-skill", "Demo", "1.0.0", "sha256:" + "0" * 64, ("skill.execute",), ("linux",), {"source": "test"}, "ok.py")
        request = ExecutionRequest(request_id, (sys.executable, "ok.py"), str(self.workspace), (Path(sys.executable).name,), skill_id="demo-skill", manifest=manifest, granted_capabilities=("skill.execute",))
        result = self.runtime.run(request)
        self.assertEqual(result.status, "denied")
        self.assertEqual(result.reason, "manifest_requires_hardened_sandbox")

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

    @unittest.skipUnless(__import__("os").name == "posix", "process-group semantics require POSIX")
    def test_timeout_terminates_non_cooperative_descendant_tree(self):
        request_id = self._approved_request(target="tree.py")
        result = self.runtime.run(self._request(request_id, script="tree.py", timeout=0.1))
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
        python3 = _sandbox_interpreter()
        argv = (python3, "ok.py")
        skip_reason = _bubblewrap_skip_reason(backend, self.workspace, argv)
        if skip_reason:
            self.skipTest(skip_reason)
        request_id = self._approved_request()
        runtime = ChildExecutionRuntime(self.gate, sandbox_backend=backend)
        request = ExecutionRequest(request_id, argv, str(self.workspace), (Path(python3).name,))
        result = runtime.run(request)
        self.assertEqual(result.status, "completed")
        self.assertTrue(result.sandboxed)
        self.assertIn("child-ok", result.stdout)

    def test_bubblewrap_manifest_runtime_blocks_host_filesystem_and_network(self):
        backend = BubblewrapBackend()
        probe = self.workspace / "probe.py"
        probe.write_text("import pathlib, socket\ntry:\n pathlib.Path('/home/ubuntu/noesis-p3/README.md').read_text(); print('host_read=allowed')\nexcept Exception:\n print('host_read=blocked')\ntry:\n socket.create_connection(('1.1.1.1', 80), 0.2); print('network=allowed')\nexcept Exception:\n print('network=blocked')\n", encoding="utf-8")
        python3 = _sandbox_interpreter()
        argv = (python3, "probe.py")
        skip_reason = _bubblewrap_skip_reason(backend, self.workspace, argv)
        if skip_reason:
            self.skipTest(skip_reason)
        request_id = self._approved_request(target="probe.py")
        manifest = SkillManifest("demo-skill", "Demo", "1.0.0", "sha256:" + "0" * 64, ("skill.execute",), ("linux",), {"source": "test"}, "probe.py")
        request = ExecutionRequest(request_id, argv, str(self.workspace), (Path(python3).name,), skill_id="demo-skill", manifest=manifest, granted_capabilities=("skill.execute",))
        result = ChildExecutionRuntime(self.gate, sandbox_backend=backend).run(request)
        self.assertEqual(result.status, "completed")
        self.assertTrue(result.sandboxed)
        self.assertIn("host_read=blocked", result.stdout)
        self.assertIn("network=blocked", result.stdout)

    def test_recovery_bound_runtime_denies_replay_and_request_identity_conflict(self):
        root = Path(self.tmp.name)
        receipts = ExecutionReceiptStore(str(root / "receipts.db"), signing_key=b"gate3-receipt-signing-key")
        recovery = ExecutionRecoveryStore(str(root / "recovery.db"))
        runtime = ChildExecutionRuntime(self.gate, receipt_store=receipts, recovery_store=recovery)
        request_id = self._approved_request()
        request = self._request(request_id)
        first = runtime.run(request)
        self.assertEqual(first.status, "completed")
        self.assertIsNotNone(first.receipt)
        replay = runtime.run(request)
        self.assertEqual(replay.status, "denied")
        self.assertEqual(replay.reason, "execution_replay_denied")
        changed = self._request(request_id, script="slow.py")
        conflict = runtime.run(changed)
        self.assertEqual(conflict.status, "denied")
        self.assertEqual(conflict.reason, "execution_request_identity_conflict")
        stored = receipts.get(first.receipt.receipt_id)
        self.assertIsNotNone(stored)
        self.assertEqual(recovery.get(request_id)["status"], "completed")

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

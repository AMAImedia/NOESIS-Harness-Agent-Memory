"""Fail-closed tests for the model task proxy-jail sandbox scaffold."""
import tempfile
import unittest
from pathlib import Path

from noesis_harness import model_task_sandbox
from noesis_harness.model_task_sandbox import (
    DEFAULT_UNAVAILABLE_REASON,
    LOOPBACK_NO_PROXY_ENTRIES,
    ModelTaskSandboxBackend,
    network_inventory,
    proxy_env_for,
)

ALLOWLIST = ("api.openai.com", "api.anthropic.com")


class ModelTaskSandboxBackendTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(tempfile.mkdtemp(prefix="noesis_model_task_sandbox_"))

    def test_default_backend_is_unavailable_and_never_passes(self):
        backend = ModelTaskSandboxBackend(allowlisted_hosts=ALLOWLIST)
        self.assertFalse(backend.available)
        self.assertEqual(backend.unavailability_reason(), DEFAULT_UNAVAILABLE_REASON)

    def test_run_returns_blocked_without_subprocess_when_unavailable(self):
        backend = ModelTaskSandboxBackend(allowlisted_hosts=ALLOWLIST)
        result = backend.run(("python", "-c", "print(1)"), self.workspace)
        self.assertEqual(result.status, "blocked")
        self.assertIsNone(result.returncode)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.reason)

    def test_injected_verifier_returning_true_makes_available_but_run_stays_blocked(self):
        backend = ModelTaskSandboxBackend(allowlisted_hosts=ALLOWLIST, verify_proxy_boundary=lambda: True)
        self.assertTrue(backend.available)
        result = backend.run(("python", "-c", "print(1)"), self.workspace)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.reason, "model_task_execution_runtime_not_bound")

    def test_verifier_false_and_raising_stay_unavailable(self):
        failing = ModelTaskSandboxBackend(allowlisted_hosts=ALLOWLIST, verify_proxy_boundary=lambda: False)
        raising = ModelTaskSandboxBackend(allowlisted_hosts=ALLOWLIST, verify_proxy_boundary=lambda: 1 / 0)
        self.assertFalse(failing.available)
        self.assertFalse(raising.available)
        expected = "model_task_proxy_boundary_check_failed"
        self.assertEqual(failing.unavailability_reason(), expected)
        self.assertEqual(raising.unavailability_reason(), expected)

    def test_proxy_env_contains_uppercase_and_lowercase_entries(self):
        env = proxy_env_for(ALLOWLIST)
        endpoint = "http://127.0.0.1:0"
        self.assertEqual(
            sorted(env.keys()),
            ["HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "no_proxy"],
        )
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            self.assertEqual(env[key], endpoint)

    def test_no_proxy_excludes_loopback_only(self):
        env = proxy_env_for(ALLOWLIST)
        for key in ("NO_PROXY", "no_proxy"):
            entries = env[key].split(",")
            self.assertEqual(entries, list(LOOPBACK_NO_PROXY_ENTRIES))
            for host in ALLOWLIST:
                self.assertNotIn(host, entries)

    def test_proxy_env_renders_custom_port(self):
        env = proxy_env_for(ALLOWLIST, port=18080)
        self.assertEqual(env["HTTP_PROXY"], "http://127.0.0.1:18080")

    def test_proxy_env_rejects_invalid_port(self):
        with self.assertRaises(ValueError):
            proxy_env_for(ALLOWLIST, port=-1)
        with self.assertRaises(ValueError):
            proxy_env_for(ALLOWLIST, port=65536)

    def test_allowlist_validation_fail_closed_on_empty_or_missing(self):
        for bad in (None, (), [], ""):
            with self.assertRaises(ValueError):
                ModelTaskSandboxBackend(allowlisted_hosts=bad)
            with self.assertRaises(ValueError):
                proxy_env_for(bad)

    def test_allowlist_rejects_bare_string_input(self):
        with self.assertRaises(ValueError):
            model_task_sandbox.validate_allowlist("api.example.com")

    def test_allowlist_validation_fail_closed_on_invalid_hosts(self):
        invalid = (
            "http://api.example.com",
            "api.example.com:443",
            "*.example.com",
            "api.example.com/path",
            "-leading.hyphen",
            "trailing-",
            "under_score.example.com",
            "bad host",
            "",
            "   ",
            123,
        )
        for host in invalid:
            with self.assertRaises(ValueError):
                model_task_sandbox.validate_allowlist((host,))

    def test_valid_allowlist_is_normalized_deterministically(self):
        normalized = model_task_sandbox.validate_allowlist(("API.Example.COM", "api.example.com", "Api.Example.Com"))
        self.assertEqual(normalized, ("api.example.com",))

    def test_egress_policy_marks_advisory_enforcement(self):
        backend = ModelTaskSandboxBackend(allowlisted_hosts=ALLOWLIST)
        policy = backend.egress_policy()
        self.assertEqual(policy["default"], "deny")
        self.assertEqual(policy["allowed_hosts"], list(ALLOWLIST))
        self.assertEqual(policy["enforcement_strength"], "advisory")
        self.assertIn("not_contained", str(policy["known_escape"]))
        self.assertEqual(policy["execution_claim"], "not_run")

    def test_network_inventory_claims_not_run_with_unverified_boundary(self):
        inventory = network_inventory()
        self.assertFalse(inventory["boundary_verified"])
        self.assertEqual(inventory["execution_claim"], "not_run")
        self.assertEqual(inventory["host_platform"], "any")

    def test_repeated_calls_are_deterministic(self):
        first = network_inventory()
        second = network_inventory()
        self.assertEqual(first, second)
        env_a = proxy_env_for(ALLOWLIST)
        env_b = proxy_env_for(ALLOWLIST)
        self.assertEqual(env_a, env_b)
        backend_a = ModelTaskSandboxBackend(allowlisted_hosts=ALLOWLIST, verify_proxy_boundary=lambda: True)
        backend_b = ModelTaskSandboxBackend(allowlisted_hosts=ALLOWLIST, verify_proxy_boundary=lambda: True)
        self.assertEqual(backend_a.egress_policy(), backend_b.egress_policy())
        self.assertEqual(
            backend_a.run(("py",), self.workspace).status,
            backend_b.run(("py",), self.workspace).status,
        )

    def test_module_never_imports_subprocess(self):
        self.assertNotIn("subprocess", vars(model_task_sandbox))


if __name__ == "__main__":
    unittest.main(verbosity=2)

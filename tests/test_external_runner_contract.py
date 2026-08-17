from __future__ import annotations

import unittest

from scripts.external_runner_contract import make_spec, validate_result


class ExternalRunnerContractTests(unittest.TestCase):
    def test_spec_is_pinned_and_shell_safe(self):
        spec = make_spec("hermes", "rev-hermes-123", ["hermes", "--query", "task"], "a" * 64)
        self.assertEqual(spec["schema_version"], "noesis.external-runner.v1")
        self.assertEqual(spec["execution"], "not_started")
        self.assertEqual(spec["workspace"], {"mode": "disposable", "outside_access": "deny", "credentials": "absent"})
        self.assertIsInstance(spec["argv"], list)
        self.assertNotIsInstance(spec["argv"], str)

    def test_result_validation_accepts_explicit_not_run(self):
        spec = make_spec("opencode", "rev-opencode-123", ["opencode", "run"], "b" * 64)
        result = {**spec, "status": "not_run", "execution": "not_run"}
        ok, errors = validate_result(result)
        self.assertTrue(ok)
        self.assertEqual(errors, ())

    def test_result_validation_rejects_shell_string_and_non_disposable_workspace(self):
        spec = make_spec("noesis", "local-sha", ["python", "run"], "c" * 64)
        result = {**spec, "status": "passed", "argv": "python run", "workspace": {"mode": "shared"}}
        ok, errors = validate_result(result)
        self.assertFalse(ok)
        self.assertIn("argv_must_be_array", errors)
        self.assertIn("workspace_not_disposable", errors)

    def test_unknown_system_and_empty_revision_fail_closed(self):
        with self.assertRaises(ValueError):
            make_spec("unknown", "rev", ["runner"], "d" * 64)
        with self.assertRaises(ValueError):
            make_spec("noesis", "", ["runner"], "d" * 64)


if __name__ == "__main__":
    unittest.main()

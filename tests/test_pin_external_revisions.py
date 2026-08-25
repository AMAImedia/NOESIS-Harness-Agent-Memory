import contextlib
import copy
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.pin_external_revisions import (
    canonical_digest,
    main,
    parse_head_revision,
)
from scripts.pinned_lane_orchestrator import validate_pinned_manifest

SHA_HERMES = "a" * 40
SHA_OPENCODE = "b" * 40
SHA_DEEPSEEK = "c" * 40

URLS = {
    "hermes": "https://github.com/NousResearch/hermes-agent",
    "opencode": "https://github.com/anomalyco/opencode",
    "deepseek_harness": "https://github.com/deepseek-ai/deepseek-harness",
}

SHAS = {
    URLS["hermes"]: SHA_HERMES,
    URLS["opencode"]: SHA_OPENCODE,
    URLS["deepseek_harness"]: SHA_DEEPSEEK,
}


def _canned_run(failures=None):
    failures = failures or {}

    def fake_run(command, **kwargs):
        assert command[0] == "git", command
        assert command[1] == "ls-remote", command
        assert len(command) == 4 and command[3] == "HEAD", command
        assert kwargs.get("timeout") == 60
        url = command[2]
        mode = failures.get(url)
        if mode == "error":
            return subprocess.CompletedProcess(command, 128, stdout="", stderr="fatal: could not read from remote repository\n")
        if mode == "timeout":
            raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs.get("timeout", 60))
        if mode == "short_sha":
            return subprocess.CompletedProcess(command, 0, stdout="abc123\tHEAD\n", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout=SHAS[url] + "\tHEAD\n", stderr="")

    return fake_run


def _collect_json_keys(node, keys):
    if isinstance(node, dict):
        for key, value in node.items():
            keys.append(key)
            _collect_json_keys(value, keys)
    elif isinstance(node, list):
        for item in node:
            _collect_json_keys(item, keys)


class PinExternalRevisionsTests(unittest.TestCase):
    def test_all_probes_ok_writes_validated_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "draft.json"
            with mock.patch("scripts.pin_external_revisions.subprocess.run", side_effect=_canned_run()):
                code = main(["--output", str(output)])
            self.assertEqual(code, 0)
            manifest = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(validate_pinned_manifest(manifest), ())
        self.assertEqual(manifest["schema_version"], "noesis.external-ab.v1")
        self.assertEqual(manifest["revision_policy"], "pin_exact_commit_before_run")
        for system in ("hermes", "opencode", "deepseek_harness"):
            self.assertIn(system, manifest["systems"])
        self.assertEqual(manifest["revisions"], {"hermes": SHA_HERMES, "opencode": SHA_OPENCODE, "deepseek_harness": SHA_DEEPSEEK})
        expected_seed = hashlib.sha256(json.dumps(manifest["revisions"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        self.assertEqual(manifest["seed_sha256"], expected_seed)
        self.assertEqual(manifest["workspace"], {"disposable": True, "seed_sha256_required": True, "outside_workspace_access": "deny", "model_artifacts": "not_allowed"})
        self.assertEqual(manifest["budgets"]["network"], "deny_by_default")
        self.assertGreater(manifest["budgets"]["wall_time_seconds"], 0)
        self.assertGreater(manifest["budgets"]["agent_steps"], 0)

    def test_no_timestamp_keys_anywhere(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "draft.json"
            with mock.patch("scripts.pin_external_revisions.subprocess.run", side_effect=_canned_run()):
                main(["--output", str(output)])
            manifest = json.loads(output.read_text(encoding="utf-8"))
        keys = []
        _collect_json_keys(manifest, keys)
        self.assertFalse([key for key in keys if "timestamp" in key.lower() or key.lower().endswith("_at")])

    def test_failed_probe_keeps_empty_revision_and_current_validator_semantics(self):
        buffer = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "draft.json"
            failures = {URLS["deepseek_harness"]: "error"}
            with mock.patch("scripts.pin_external_revisions.subprocess.run", side_effect=_canned_run(failures)), contextlib.redirect_stdout(buffer):
                code = main(["--output", str(output)])
            manifest = json.loads(output.read_text(encoding="utf-8"))
        report = json.loads(buffer.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(manifest["revisions"]["deepseek_harness"], "")
        self.assertEqual(manifest["revisions"]["hermes"], SHA_HERMES)
        deepseek_probe = report["probed"]["deepseek_harness"]
        self.assertFalse(deepseek_probe["ok"])
        self.assertEqual(deepseek_probe["revision"], "")
        self.assertTrue(deepseek_probe["reason"].startswith("git_ls_remote_failed:"))
        # Current validator semantics: an empty revision is not a validation
        # error; required_external_system_missing fires only when the system
        # NAME is absent from manifest["systems"].
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["validated_ok"])
        self.assertEqual(validate_pinned_manifest(manifest), ())
        self.assertNotIn("required_external_system_missing", validate_pinned_manifest(manifest))

    def test_timeout_probe_is_recorded_as_reason(self):
        buffer = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "draft.json"
            failures = {URLS["opencode"]: "timeout"}
            with mock.patch("scripts.pin_external_revisions.subprocess.run", side_effect=_canned_run(failures)), contextlib.redirect_stdout(buffer):
                main(["--output", str(output)])
        report = json.loads(buffer.getvalue())
        self.assertTrue(report["probed"]["opencode"]["reason"].startswith("git_ls_remote_timeout:"))
        self.assertFalse(report["probed"]["opencode"]["ok"])

    def test_required_system_missing_only_when_name_absent_from_systems(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "draft.json"
            with mock.patch("scripts.pin_external_revisions.subprocess.run", side_effect=_canned_run()):
                main(["--output", str(output)])
            manifest = json.loads(output.read_text(encoding="utf-8"))
        broken = copy.deepcopy(manifest)
        broken["systems"] = [system for system in broken["systems"] if system != "hermes"]
        self.assertIn("required_external_system_missing", validate_pinned_manifest(broken))
        self.assertNotIn("required_external_system_missing", validate_pinned_manifest(manifest))

    def test_invalid_short_sha_is_rejected_and_never_written(self):
        buffer = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "draft.json"
            failures = {URLS["opencode"]: "short_sha"}
            with mock.patch("scripts.pin_external_revisions.subprocess.run", side_effect=_canned_run(failures)), contextlib.redirect_stdout(buffer):
                main(["--output", str(output)])
            manifest = json.loads(output.read_text(encoding="utf-8"))
        report = json.loads(buffer.getvalue())
        self.assertEqual(parse_head_revision("abc123\tHEAD\n"), "")
        self.assertEqual(manifest["revisions"]["opencode"], "")
        self.assertEqual(report["probed"]["opencode"]["reason"], "no_exact_head_revision_in_output")
        self.assertEqual(validate_pinned_manifest(manifest), ())

    def test_parse_head_revision_accepts_only_exact_commits(self):
        self.assertEqual(parse_head_revision(SHA_DEEPSEEK + "\tHEAD\n"), SHA_DEEPSEEK)
        self.assertEqual(parse_head_revision(("F" * 40) + "\trefs/heads/main\n"), "f" * 40)
        self.assertEqual(parse_head_revision(("d" * 64) + "\tHEAD\n"), "d" * 64)
        self.assertEqual(parse_head_revision("abc123\tHEAD\n"), "")
        self.assertEqual(parse_head_revision(""), "")
        self.assertEqual(parse_head_revision("not-a-sha\tHEAD\n"), "")

    def test_seed_is_deterministic_across_runs(self):
        manifests = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "draft.json"
                with mock.patch("scripts.pin_external_revisions.subprocess.run", side_effect=_canned_run()):
                    main(["--output", str(output)])
                manifests.append(json.loads(output.read_text(encoding="utf-8")))
        self.assertEqual(manifests[0], manifests[1])
        revisions = {"hermes": SHA_HERMES, "opencode": SHA_OPENCODE, "deepseek_harness": SHA_DEEPSEEK}
        self.assertEqual(manifests[0]["seed_sha256"], canonical_digest(revisions))


if __name__ == "__main__":
    unittest.main(verbosity=2)

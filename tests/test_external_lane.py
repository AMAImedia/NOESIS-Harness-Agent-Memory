from __future__ import annotations

import concurrent.futures
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

from scripts.external_runner_contract import make_spec
from scripts.run_external_lane import create_approval_receipt, consume_approval_receipt, main, plan, verify_approval_receipt


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
            receipt_path = root / "approval.json"
            receipt_store = root / "consumed.json"
            key = "approval-key-for-tests-2026"
            spec = make_spec("hermes", "pinned-h1", [sys.executable, "-c", "print('fixture-run')"], "c" * 64)
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            receipt = create_approval_receipt(plan(spec, str(root)), key, now=time.time(), ttl_seconds=300, nonce="run-1")
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
            code = main(["--spec", str(spec_path), "--workspace", str(root), "--output", str(output), "--execute", "--approve", "--approval-receipt", str(receipt_path), "--approval-key", key, "--receipt-store", str(receipt_store)])
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(code, 0)
            self.assertEqual(report["execution"], "started")
            self.assertEqual(report["status"], "passed")
            self.assertEqual(report["stdout"].strip(), "fixture-run")

    def test_approval_rejects_mutation_expiry_and_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = "approval-key-for-tests-2026"
            spec = make_spec("hermes", "pinned-h1", [sys.executable, "-c", "print('x')"], "d" * 64)
            report = plan(spec, str(root))
            receipt = create_approval_receipt(report, key, now=100.0, ttl_seconds=10, nonce="fixed")
            mutated = dict(report, revision="other")
            self.assertEqual(verify_approval_receipt(receipt, mutated, key, now=101.0), (False, "approval_plan_identity_mismatch"))
            self.assertEqual(verify_approval_receipt(receipt, report, key, now=111.0), (False, "approval_expired"))
            store = root / "used.json"
            self.assertEqual(consume_approval_receipt(receipt, str(store)), (True, "consumed"))
            self.assertEqual(consume_approval_receipt(receipt, str(store)), (False, "approval_replay"))

    def test_corrupted_store_fails_closed_and_reopen_preserves_replay(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = "approval-key-for-tests-2026"
            spec = make_spec("hermes", "pinned-h1", [sys.executable, "-c", "print('x')"], "f" * 64)
            receipt = create_approval_receipt(plan(spec, str(root)), key, now=time.time(), ttl_seconds=300, nonce="reopen")
            store = root / "consumed.sqlite"
            self.assertEqual(consume_approval_receipt(receipt, str(store)), (True, "consumed"))
            self.assertEqual(consume_approval_receipt(receipt, str(store)), (False, "approval_replay"))
            corrupt = root / "corrupt.sqlite"
            corrupt.write_bytes(b"not-a-sqlite-database")
            self.assertEqual(consume_approval_receipt(receipt, str(corrupt)), (False, "approval_store_invalid"))

    def test_concurrent_consume_has_one_winner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            key = "approval-key-for-tests-2026"
            spec = make_spec("hermes", "pinned-h1", [sys.executable, "-c", "print('x')"], "e" * 64)
            receipt = create_approval_receipt(plan(spec, str(root)), key, now=time.time(), ttl_seconds=300, nonce="concurrent")
            store = root / "consumed.sqlite"
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda _: consume_approval_receipt(receipt, str(store)), range(8)))
            self.assertEqual(sum(result == (True, "consumed") for result in results), 1)
            self.assertEqual(sum(result == (False, "approval_replay") for result in results), 7)


if __name__ == "__main__":
    unittest.main()

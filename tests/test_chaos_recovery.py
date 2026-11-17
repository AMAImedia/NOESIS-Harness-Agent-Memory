from __future__ import annotations

import dataclasses
import multiprocessing
import os
import tempfile
import time
import unittest
from pathlib import Path

from noesis_harness.best_state import BestStateStore, RecoveryStatus
from noesis_harness.execution_assurance import create_receipt, verify_receipt
from noesis_harness.queue import DurableQueue


def _write_candidates(db_path: str, ready: multiprocessing.synchronize.Event) -> None:
    store = BestStateStore(db_path)
    ready.set()
    index = 0
    while True:
        store.record_candidate(
            "chaos-run",
            float(index % 17) / 17.0,
            {"step": index, "payload": "x" * 256},
        )
        index += 1


class ChaosRecoveryTests(unittest.TestCase):
    def test_kill_during_write_leaves_reopenable_consistent_store(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "best.db")
            BestStateStore(db_path)
            ready = multiprocessing.Event()
            process = multiprocessing.Process(target=_write_candidates, args=(db_path, ready))
            process.start()
            startup_timeout = 30 if os.name == "nt" else 5
            self.assertTrue(ready.wait(startup_timeout), "writer did not initialize")

            time.sleep(0.08)
            process.terminate()
            process.join(5)
            if process.is_alive():
                process.kill()
                process.join(5)
            reopened = BestStateStore(db_path)
            history = reopened.history("chaos-run")
            current = reopened.current("chaos-run")
            best = reopened.best("chaos-run")
            self.assertIsNotNone(current)
            self.assertIsNotNone(best)
            self.assertGreaterEqual(len(history), 1)
            self.assertIn(current.state_id, {state.state_id for state in history})
            self.assertIn(best.state_id, {state.state_id for state in history})

    def test_interrupted_provider_response_is_requeued_and_retryable(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = DurableQueue(str(Path(directory) / "queue.db"), max_attempts=3)
            task_id = queue.enqueue({"provider": "hermes", "request": "partial"})
            leased = queue.lease("provider-worker")
            self.assertEqual(leased[0]["id"], task_id)
            self.assertEqual(queue.stats().get("leased"), 1)
            recovered = queue.recover()
            self.assertEqual(recovered, 1)
            retry = queue.lease("provider-worker-retry")
            self.assertEqual([item["id"] for item in retry], [task_id])
            queue.ack(task_id)
            self.assertEqual(queue.stats().get("done"), 1)

    def test_corrupted_receipt_fails_closed(self):
        receipt = create_receipt(
            request={"tool": "read"},
            policy={"capability": "file.read"},
            workspace_before="sha256:before",
            workspace_after="sha256:after",
            outcome="committed",
            rollback_available=True,
        )
        corrupted = dataclasses.replace(receipt, outcome="failed")
        self.assertFalse(verify_receipt(corrupted))

    def test_best_state_recovery_is_idempotent_and_preserves_best(self):
        with tempfile.TemporaryDirectory() as directory:
            store = BestStateStore(str(Path(directory) / "best.db"))
            best = store.record_candidate("run", 0.95, {"version": "best"})
            store.record_candidate("run", 0.10, {"version": "regression"})
            recovered = store.recover("run", "provider-interrupted")
            repeated = store.recover("run", "duplicate-recovery")
            self.assertEqual(recovered.status, RecoveryStatus.RECOVERED)
            self.assertEqual(repeated.status, RecoveryStatus.NOOP)
            self.assertEqual(store.current("run").state_id, best.state.state_id)
            self.assertEqual(store.best("run").state_id, best.state.state_id)
            self.assertEqual(store.rollback_count("run"), 1)


if __name__ == "__main__":
    unittest.main()


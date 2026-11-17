import unittest

from scripts.run_task_execution_parity import run


class TaskExecutionParityTests(unittest.TestCase):
    def test_local_end_to_end_parity_and_external_boundary(self):
        report = run()
        self.assertEqual(report["schema_version"], "noesis.task-execution-parity.v1")
        self.assertEqual(report["scope"], "local_only")
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["execution"], "completed")
        self.assertEqual(report["local"]["task_state"], "review")
        self.assertEqual(report["local"]["child_status"], "completed")
        self.assertTrue(report["local"]["sse_monotonic"])
        self.assertTrue(report["local"]["recovery_requeued"])
        self.assertEqual(report["external"]["hermes"], "not_run")
        self.assertEqual(report["external"]["opencode"], "not_run")
        self.assertEqual(report["external"]["deepseek_harness"], "not_run")
        self.assertEqual(report["backend_inventory"]["macos_sandbox_exec"]["execution"], "not_run")
        self.assertEqual(report["backend_inventory"]["windows_native"]["execution"], "not_run")


if __name__ == "__main__":
    unittest.main(verbosity=2)

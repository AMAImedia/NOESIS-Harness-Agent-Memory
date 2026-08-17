import unittest

from noesis_harness.coding_adapter import PINNED_TASKS, PinnedCodingTaskAdapter


NORMALIZE = """
def normalize_words(text):
    return [word.lower() for word in text.strip().split()]
"""

SAFE_JOIN = """
from pathlib import Path

def safe_join(root, name):
    base = Path(root).resolve()
    candidate = (base / name).resolve()
    candidate.relative_to(base)
    return candidate
"""

CANONICAL = """
import json

def canonical_json(value):
    return json.dumps(value, sort_keys=True)
"""


class PinnedCodingAdapterTests(unittest.TestCase):
    def test_pinned_tasks_are_stable_and_all_valid_submissions_pass(self):
        adapter = PinnedCodingTaskAdapter()
        self.assertEqual(tuple(task.task_id for task in PINNED_TASKS), (
            "normalize-words-v1", "safe-join-v1", "canonical-json-v1"
        ))
        results = adapter.evaluate((
            ("normalize-words-v1", NORMALIZE),
            ("safe-join-v1", SAFE_JOIN),
            ("canonical-json-v1", CANONICAL),
        ))
        self.assertEqual([result.status for result in results], ["passed", "passed", "passed"])
        self.assertTrue(all(result.execution_status == "unavailable" for result in results))
        self.assertTrue(all(len(result.artifact_digest) == 64 for result in results))

    def test_missing_requirement_and_forbidden_call_fail(self):
        adapter = PinnedCodingTaskAdapter()
        missing = adapter.verify("normalize-words-v1", "def normalize_words(text): return text.strip()")
        forbidden = adapter.verify("normalize-words-v1", "def normalize_words(text): return eval(text)")
        self.assertEqual(missing.status, "failed")
        self.assertIn("call:split", missing.failed_checks)
        self.assertEqual(forbidden.status, "failed")
        self.assertTrue(any(item.startswith("forbidden_calls:") for item in forbidden.failed_checks))

    def test_parse_and_unknown_task_fail_soft(self):
        adapter = PinnedCodingTaskAdapter()
        syntax = adapter.verify("normalize-words-v1", "def normalize_words(:")
        unknown = adapter.verify("not-pinned", NORMALIZE)
        self.assertEqual(syntax.status, "failed")
        self.assertEqual(syntax.execution_status, "unavailable")
        self.assertEqual(unknown.status, "unavailable")
        self.assertEqual(unknown.execution_status, "unavailable")

    def test_summary_counts_are_deterministic(self):
        adapter = PinnedCodingTaskAdapter()
        results = adapter.evaluate((("normalize-words-v1", NORMALIZE), ("bad", "x")))
        summary = adapter.summarize(results)
        self.assertEqual(summary.task_count, 2)
        self.assertEqual(summary.passed, 1)
        self.assertEqual(summary.unavailable, 1)
        self.assertEqual(summary.failed, 0)
        self.assertEqual(summary.pass_rate, 0.5)
        self.assertEqual(summary.execution_status, "unavailable")


if __name__ == "__main__":
    unittest.main()

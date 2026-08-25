import dataclasses
import json
import tempfile
import unittest

from noesis_harness.parallel_agent import AgentLane, AgentLaneResult, SafeParallelExecutor
from noesis_harness.protocol_leakage_holdouts import (
    PROTOCOL_LEAKAGE_SCHEMA,
    RESULT_REQUIRED_KEYS,
    SINK_ALLOWED_KEYS,
    ProtocolLeakageSuite,
    envelope_violation,
    redaction_violation,
    scoping_violation,
)


class _LeakyWorkspaceEventSinkExecutor(SafeParallelExecutor):
    """Simulated leaky provider: echoes the absolute workspace root into every
    payload crossing the event_sink boundary."""

    def execute(self, lanes, callback, *, event_sink=None, **kwargs):
        if event_sink is None:
            return super().execute(lanes, callback, **kwargs)
        leaked_root = str(self.workspace_root)

        def leaky(event):
            enriched = dict(event)
            enriched["workspace"] = leaked_root
            event_sink(enriched)

        return super().execute(lanes, callback, event_sink=leaky, **kwargs)


class ProtocolLeakageSuiteTests(unittest.TestCase):
    def test_all_holdouts_pass(self):
        suite = ProtocolLeakageSuite()
        results = suite.evaluate()
        self.assertEqual(tuple(result.case_id for result in results), suite.CASE_IDS)
        self.assertEqual(len(results), 4)
        self.assertTrue(all(result.passed for result in results), results)
        self.assertEqual(suite.pass_rate(), 1.0)

    def test_holdouts_are_deterministic(self):
        suite = ProtocolLeakageSuite()
        first = [(result.case_id, result.passed) for result in suite.evaluate()]
        second = [(result.case_id, result.passed) for result in suite.evaluate()]
        self.assertEqual(first, second)

    def test_summary_schema(self):
        summary = ProtocolLeakageSuite().summary()
        self.assertEqual(summary["schema_version"], PROTOCOL_LEAKAGE_SCHEMA)
        self.assertEqual(PROTOCOL_LEAKAGE_SCHEMA, "noesis.protocol-leakage.v1")
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["passed"] + summary["failed"], summary["total"])
        self.assertEqual(len(summary["cases"]), 4)
        self.assertEqual(
            tuple(case["case_id"] for case in summary["cases"]),
            ProtocolLeakageSuite.CASE_IDS,
        )
        self.assertAlmostEqual(summary["pass_rate"], 1.0)

    def test_live_event_sink_payloads_are_minimal(self):
        with tempfile.TemporaryDirectory(prefix="noesis-proto-live-sink-") as root:
            executor = SafeParallelExecutor(root, max_concurrency=2)
            seen = []

            def sink(event):
                seen.append(dict(event))

            results = executor.execute(
                [AgentLane("live-agent-a", "live-task-a", "live-ws-a"), AgentLane("live-agent-b", "live-task-b", "live-ws-b")],
                lambda ctx: {"echo": str(ctx.workspace)},
                session_id="proto-live-sink",
                event_sink=sink,
            )
            self.assertTrue(all(result.status == "passed" for result in results))
            self.assertGreaterEqual(len(seen), 4)
            for event in seen:
                self.assertLessEqual(set(event.keys()), set(SINK_ALLOWED_KEYS), event)
                self.assertEqual(event["session_id"], "proto-live-sink")
            violation = redaction_violation(seen, [result.workspace for result in results])
            self.assertEqual(violation, "")

    def test_result_envelope_contract_matches_required_keys(self):
        self.assertTrue(RESULT_REQUIRED_KEYS <= {field.name for field in dataclasses.fields(AgentLaneResult)})
        clean = AgentLaneResult("s", "t", "a", "w", "passed")
        self.assertEqual(envelope_violation([clean]), "")


class ProtocolLeakageNegativeInjectionTests(unittest.TestCase):
    def test_detector_catches_leaky_event_sink_executor(self):
        suite = ProtocolLeakageSuite(
            executor_factory=lambda root: _LeakyWorkspaceEventSinkExecutor(root, max_concurrency=3)
        )
        by_case = {result.case_id: result for result in suite.evaluate()}
        self.assertFalse(by_case["event_sink_redaction"].passed)
        self.assertIn("extra_keys", by_case["event_sink_redaction"].observed)
        for other in ("audit_error_isolation", "result_envelope_typing", "cross_session_event_scoping"):
            self.assertTrue(by_case[other].passed, other)

    def test_redaction_detector_flags_extra_key_and_canary(self):
        canary_workspace = "B:\\somewhere\\noesis-proto-root"
        leaky = [
            {"kind": "lane_started", "session_id": "s", "task_id": "t", "agent_id": "a"},
            {
                "kind": "lane_completed",
                "session_id": "s",
                "task_id": "t",
                "agent_id": "a",
                "workspace": canary_workspace,
                "output_preview": "CANARY-CALLBACK-OUTPUT-91f3",
            },
        ]
        observed = redaction_violation(leaky, [canary_workspace, "CANARY-CALLBACK-OUTPUT-91f3"])
        self.assertIn("extra_keys=output_preview,workspace", observed)
        self.assertEqual(redaction_violation([{"kind": "lane_started", "session_id": "s", "task_id": "t", "agent_id": "a"}], [canary_workspace]), "")
        # Windows backslash paths are JSON-escaped in a serialized blob; the
        # detector walks values instead, so it still finds the raw needle.
        escaped_only = json.dumps({"workspace": canary_workspace})
        self.assertNotIn(canary_workspace, escaped_only)
        self.assertNotEqual("", redaction_violation([json.loads(escaped_only)], [canary_workspace]))

    def test_envelope_detector_flags_injected_field(self):
        tampered = AgentLaneResult("s", "t", "a", "w", "passed")
        object.__setattr__(tampered, "credentials", "secret-token")
        observed = envelope_violation([tampered])
        self.assertIn("extra_fields=credentials", observed)
        missing = AgentLaneResult("s", "", "a", "w", "passed")
        self.assertIn("task_id_untyped", envelope_violation([missing]))

    def test_scoping_detector_flags_foreign_session(self):
        mismatched = [{"kind": "lane_started", "session_id": "other-session", "task_id": "t", "agent_id": "a"}]
        self.assertIn("session_mismatch", scoping_violation(mismatched, "expected-session", []))
        embedded = [
            {
                "kind": "lane_completed",
                "session_id": "expected-session",
                "task_id": "t",
                "agent_id": "a",
                "note": "carried over from proto-session-foreign-dead",
            }
        ]
        self.assertIn(
            "foreign_session_marker=proto-session-foreign-dead",
            scoping_violation(embedded, "expected-session", ["proto-session-foreign-dead"]),
        )

    def test_fail_closed_on_executor_factory_failure(self):
        def broken_factory(root):
            raise RuntimeError("factory unavailable")

        suite = ProtocolLeakageSuite(executor_factory=broken_factory)
        results = suite.evaluate()
        self.assertEqual(len(results), 4)
        self.assertTrue(all(not result.passed for result in results), results)
        self.assertTrue(all(result.observed.startswith("unexpected_exception:") for result in results))
        self.assertEqual(suite.summary()["pass_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()

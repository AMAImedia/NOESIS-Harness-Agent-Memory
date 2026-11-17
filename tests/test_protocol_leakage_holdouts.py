import dataclasses
import json
import os
import tempfile
import unittest

from noesis_harness.parallel_agent import AgentLane, AgentLaneResult, SafeParallelExecutor
from noesis_harness.protocol_leakage_holdouts import (
    PROTOCOL_LEAKAGE_SCHEMA,
    RESULT_REQUIRED_KEYS,
    SINK_ALLOWED_KEYS,
    ProtocolLeakageSuite,
    digest_isolation_violation,
    envelope_violation,
    marker_scope_violation,
    redaction_violation,
    scoping_violation,
)
from noesis_harness.work_product_benchmark import (
    MARKER_STATUS_COMMITTED,
    WorkProductBenchmarkError,
    WorkProductCommitMarker,
    WorkProductCommitMarkerLedger,
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


class _DigestCarryoverExecutor(SafeParallelExecutor):
    """Simulated cross-run leakage: once one session has produced aggregate
    digests, every later session's lane_completed events carry the previous
    session's first digest smuggled inside an otherwise allowed field."""

    def __init__(self, workspace_root, *, max_concurrency: int = 2):
        super().__init__(workspace_root, max_concurrency=max_concurrency)
        self._prior_digests = ()

    def _harvest(self, results):
        digests = []
        for result in results:
            output = getattr(result, "output", None)
            if isinstance(output, dict) and isinstance(output.get("aggregate_digest"), str):
                digests.append(output["aggregate_digest"])
        self._prior_digests = tuple(digests)

    def execute(self, lanes, callback, *, event_sink=None, **kwargs):
        prior = self._prior_digests

        def wrapped(event):
            enriched = dict(event)
            if prior and event.get("kind") == "lane_completed":
                enriched["agent_id"] = "%s|%s" % (event.get("agent_id", ""), prior[0])
            if event_sink is not None:
                event_sink(enriched)

        results = super().execute(lanes, callback, event_sink=wrapped, **kwargs)
        self._harvest(results)
        return results


class ProtocolLeakageSuiteTests(unittest.TestCase):
    def test_all_holdouts_pass(self):
        suite = ProtocolLeakageSuite()
        results = suite.evaluate()
        self.assertEqual(tuple(result.case_id for result in results), suite.CASE_IDS)
        self.assertEqual(len(results), 6)
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
        self.assertEqual(summary["total"], 6)
        self.assertEqual(summary["passed"] + summary["failed"], summary["total"])
        self.assertEqual(len(summary["cases"]), 6)
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

    def test_event_sink_failed_is_declared_envelope_field(self):
        names = {field.name for field in dataclasses.fields(AgentLaneResult)}
        self.assertIn("event_sink_failed", names)
        field = next(f for f in dataclasses.fields(AgentLaneResult) if f.name == "event_sink_failed")
        self.assertEqual(field.default, False)
        self.assertEqual(field.type, "bool")
        flagged = AgentLaneResult("s", "t", "a", "w", "passed", event_sink_failed=True)
        self.assertTrue(flagged.event_sink_failed)
        self.assertEqual(envelope_violation([flagged]), "")


class ProtocolLeakageNegativeInjectionTests(unittest.TestCase):
    def test_detector_catches_leaky_event_sink_executor(self):
        suite = ProtocolLeakageSuite(
            executor_factory=lambda root: _LeakyWorkspaceEventSinkExecutor(root, max_concurrency=3)
        )
        by_case = {result.case_id: result for result in suite.evaluate()}
        self.assertFalse(by_case["event_sink_redaction"].passed)
        self.assertIn("extra_keys", by_case["event_sink_redaction"].observed)
        for other in (
            "audit_error_isolation",
            "result_envelope_typing",
            "cross_session_event_scoping",
            "aggregate_digest_isolation",
            "marker_binding_scope",
        ):
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

    def test_envelope_detector_still_rejects_unknown_keys_with_new_field_declared(self):
        tampered = AgentLaneResult("s", "t", "a", "w", "passed", event_sink_failed=True)
        object.__setattr__(tampered, "sink_error_detail", "internal sink stack trace")
        observed = envelope_violation([tampered])
        self.assertIn("extra_fields=sink_error_detail", observed)

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
        self.assertEqual(len(results), 6)
        by_case = {result.case_id: result for result in results}
        # Every executor-backed holdout fails closed on the unknown exception.
        for case_id in ("event_sink_redaction", "audit_error_isolation", "result_envelope_typing",
                        "cross_session_event_scoping", "aggregate_digest_isolation"):
            self.assertFalse(by_case[case_id].passed, case_id)
            self.assertTrue(by_case[case_id].observed.startswith("unexpected_exception:"), case_id)
        # The marker ledger holdout never touches the executor and stays green.
        self.assertTrue(by_case["marker_binding_scope"].passed)
        self.assertEqual(suite.summary()["failed"], 5)

    def test_digest_carryover_executor_detected_by_holdout_1(self):
        suite = ProtocolLeakageSuite(
            executor_factory=lambda root: _DigestCarryoverExecutor(root, max_concurrency=2)
        )
        by_case = {result.case_id: result for result in suite.evaluate()}
        self.assertFalse(by_case["aggregate_digest_isolation"].passed)
        self.assertIn("foreign_digest", by_case["aggregate_digest_isolation"].observed)
        for other in (
            "event_sink_redaction",
            "audit_error_isolation",
            "result_envelope_typing",
            "cross_session_event_scoping",
            "marker_binding_scope",
        ):
            self.assertTrue(by_case[other].passed, other)


class DigestIsolationDetectorTests(unittest.TestCase):
    @staticmethod
    def _lane_result(session_id, task_id, digest_value):
        return AgentLaneResult(
            session_id,
            task_id,
            task_id + "-agent",
            "ws-" + task_id,
            "passed",
            output={"aggregate": {"task": task_id}, "aggregate_digest": digest_value},
        )

    def test_clean_surfaces_pass(self):
        own = "a" * 64
        foreign = "b" * 64
        events = [{"kind": "lane_started", "session_id": "s-a", "task_id": "t", "agent_id": "a"}]
        audit = [{"event": "lane_completed", "session_id": "s-a", "task_id": "t", "agent_id": "a"}]
        results = [self._lane_result("s-a", "t", own)]
        self.assertEqual(digest_isolation_violation(events, results, audit, [own], [foreign]), "")

    def test_foreign_digest_in_each_surface_flagged(self):
        own = "c" * 64
        foreign = "d" * 64
        results = [self._lane_result("s-a", "t", own)]
        leaky_events = [{"kind": "lane_completed", "session_id": "s-b", "task_id": "t2", "agent_id": "x|" + foreign}]
        self.assertIn(
            "foreign_digest[0].events",
            digest_isolation_violation(leaky_events, results, [], [own], [foreign]),
        )
        leaked_own_results = [self._lane_result("s-b", "t2", foreign), self._lane_result("s-a", "t", own)]
        self.assertIn(
            "foreign_digest[0].results",
            digest_isolation_violation([], leaked_own_results, [], [own], [foreign]),
        )
        leaky_audit = [{"event": "lane_completed", "session_id": "s-b", "note": foreign}]
        self.assertIn(
            "foreign_digest[0].audit",
            digest_isolation_violation([], results, leaky_audit, [own], [foreign]),
        )

    def test_own_digest_retention_and_privacy_enforced(self):
        own = "e" * 64
        stripped = AgentLaneResult("s-a", "t", "a", "w", "passed", output={"aggregate": {"task": "t"}})
        self.assertIn(
            "own_digest[0].missing_from_results",
            digest_isolation_violation([], [stripped], [], [own], []),
        )
        echo_event = [{"kind": "lane_completed", "session_id": "s-a", "digest_echo": own}]
        self.assertIn(
            "own_digest[0].leaked_to_events",
            digest_isolation_violation(echo_event, [self._lane_result("s-a", "t", own)], [], [own], []),
        )
        echo_audit = [{"event": "lane_completed", "session_id": "s-a", "digest_echo": own}]
        self.assertIn(
            "own_digest[0].leaked_to_audit",
            digest_isolation_violation([], [self._lane_result("s-a", "t", own)], echo_audit, [own], []),
        )


class MarkerScopeHoldoutTests(unittest.TestCase):
    def _marker(self, product_id, auth_digest):
        return WorkProductCommitMarker(
            product_id,
            product_id + "-task",
            product_id + "-agent",
            product_id + "-ws",
            product_id + "-base",
            product_id + "-head",
            product_id + "-artifact",
            auth_digest,
        )

    def test_holdout_marker_binding_scope_passes_on_real_ledger(self):
        suite = ProtocolLeakageSuite()
        by_case = {result.case_id: result for result in suite.evaluate()}
        self.assertTrue(by_case["marker_binding_scope"].passed, by_case["marker_binding_scope"].observed)
        self.assertIn("conflict_closed", by_case["marker_binding_scope"].observed)

    def test_ledger_rejects_cross_product_authorization_reuse(self):
        with tempfile.TemporaryDirectory(prefix="noesis-marker-scope-") as root:
            path = str(os.path.join(root, "commit-markers.jsonl"))
            ledger = WorkProductCommitMarkerLedger(path)
            marker_p1 = self._marker("p1", "AUTH-1")
            marker_p2 = self._marker("p2", "AUTH-2")
            self.assertEqual(ledger.record(marker_p1).status, MARKER_STATUS_COMMITTED)
            self.assertEqual(ledger.record(marker_p2).status, MARKER_STATUS_COMMITTED)
            attack = dataclasses.replace(marker_p2, authorization_digest="AUTH-1")
            with self.assertRaises(WorkProductBenchmarkError) as ctx:
                ledger.record(attack)
            self.assertNotIn("AUTH-1", str(ctx.exception))
            self.assertEqual(ledger.get("p1"), marker_p1)
            self.assertEqual(ledger.get("p2"), marker_p2)
            self.assertTrue(ledger.verify_integrity()["ok"])
            self.assertEqual(marker_scope_violation(str(ctx.exception), "AUTH-1", attack.to_mapping()), "")

    def test_detector_flags_payload_echoing_error_text(self):
        payload = self._marker("p2", "AUTH-1").to_mapping()
        echoed = "commit_marker_conflict:" + json.dumps(payload, sort_keys=True)
        self.assertIn("payload_embedded=", marker_scope_violation(echoed, "AUTH-1", payload))
        bare_ok = "commit_marker_conflict"
        self.assertEqual(marker_scope_violation(bare_ok, "AUTH-1", payload), "")
        self.assertIn("empty_error_text", marker_scope_violation("", "AUTH-1", payload))
        long_dump = "commit_marker_conflict" + ("x" * 200)
        self.assertIn("error_too_long", marker_scope_violation(long_dump, "AUTH-1", payload))

    def test_broken_ledger_subclass_caught_by_detector_logic(self):
        class _EchoingLedger(WorkProductCommitMarkerLedger):
            def record(self, marker):
                try:
                    return super().record(marker)
                except WorkProductBenchmarkError:
                    raise WorkProductBenchmarkError(
                        "commit_marker_conflict:" + json.dumps(marker.to_mapping(), sort_keys=True)
                    )

        with tempfile.TemporaryDirectory(prefix="noesis-marker-echo-") as root:
            path = str(os.path.join(root, "commit-markers.jsonl"))
            ledger = _EchoingLedger(path)
            marker_p1 = self._marker("p1", "AUTH-1")
            ledger.record(marker_p1)
            attack = dataclasses.replace(marker_p1, head_snapshot_id="divergent-head")
            conflict_text = ""
            try:
                ledger.record(attack)
            except WorkProductBenchmarkError as exc:
                conflict_text = str(exc)
            observed = marker_scope_violation(conflict_text, "AUTH-1", attack.to_mapping())
            self.assertIn("payload_embedded=", observed)
            self.assertTrue(any(
                str(value) in conflict_text for value in attack.to_mapping().values()
            ))


if __name__ == "__main__":
    unittest.main()

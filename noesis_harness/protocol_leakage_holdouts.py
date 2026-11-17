"""Deterministic protocol/provider leakage holdouts over live executor lanes.

Borrowed patterns: the fixed-corpus negative/positive holdout discipline of
noesis_harness/isolation_holdouts.py (agentmemory-style deterministic
leakage cases), the fail-closed evidence handling of agentmemory governance
writes as reused by work_product_benchmark.py (including its commit-marker
ledger conflict discipline), and the deepseek-harness bounded deterministic
rubric. Every probe runs through a real SafeParallelExecutor lane fan-out;
storage/recall/coordination never call an LLM, and any unexpected exception
classifies the case as failed, never passed.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence, Tuple

from .parallel_agent import AgentLane, AgentLaneResult, SafeParallelExecutor
from .work_product_benchmark import (
    MARKER_STATUS_COMMITTED,
    WorkProductBenchmarkError,
    WorkProductCommitMarker,
    WorkProductCommitMarkerLedger,
)


PROTOCOL_LEAKAGE_SCHEMA = "noesis.protocol-leakage.v1"

# Structural contract for payloads crossing the event_sink boundary.
SINK_ALLOWED_KEYS = frozenset({"kind", "session_id", "task_id", "agent_id", "error"})
# Core typed fields every AgentLaneResult must carry; extra runtime fields are leaks.
RESULT_REQUIRED_KEYS = frozenset({"status", "task_id", "agent_id", "workspace", "output", "error"})
LANE_RESULT_STATUSES = frozenset({"passed", "failed", "blocked", "cancelled"})


@dataclass(frozen=True)
class ProtocolLeakageResult:
    """Outcome of one deterministic protocol-level leakage holdout."""

    case_id: str
    passed: bool
    observed: str


def _contains_needle(value: object, needle: str) -> bool:
    """Recursively search a JSON-like value tree for a substring.

    Walking values directly avoids JSON escaping pitfalls (Windows backslash
    paths would never match inside a json.dumps blob).
    """
    if isinstance(value, str):
        return bool(needle) and needle in value
    if isinstance(value, Mapping):
        return any(_contains_needle(item, needle) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_needle(item, needle) for item in value)
    return False


def redaction_violation(
    payloads: Sequence[Mapping[str, object]],
    forbidden: Sequence[str],
    allowed_keys: frozenset = SINK_ALLOWED_KEYS,
) -> str:
    """Return "" when every payload stays within the allowed key envelope and
    contains none of the forbidden substrings; otherwise describe the first
    violation found."""
    for index, payload in enumerate(payloads):
        if not isinstance(payload, Mapping):
            return "payload[%d].not_mapping" % index
        extra = sorted(str(key) for key in payload.keys() if str(key) not in allowed_keys)
        if extra:
            return "payload[%d].extra_keys=%s" % (index, ",".join(extra))
        for needle in forbidden:
            if _contains_needle(payload, needle):
                return "payload[%d].forbidden_value=%s" % (index, needle)
    return ""


def envelope_violation(results: Sequence[AgentLaneResult]) -> str:
    """Return "" when every AgentLaneResult crosses only its declared typed
    fields with well-typed values; otherwise describe the first violation."""
    declared = tuple(field.name for field in dataclasses.fields(AgentLaneResult))
    declared_set = frozenset(declared)
    for index, result in enumerate(results):
        try:
            runtime_keys = frozenset(vars(result).keys())
        except TypeError:
            return "result[%d].not_a_plain_instance" % index
        extra = sorted(runtime_keys - declared_set)
        if extra:
            return "result[%d].extra_fields=%s" % (index, ",".join(extra))
        missing = sorted(RESULT_REQUIRED_KEYS - runtime_keys)
        if missing:
            return "result[%d].missing_fields=%s" % (index, ",".join(missing))
        if result.status not in LANE_RESULT_STATUSES:
            return "result[%d].status_unknown=%s" % (index, result.status)
        if not isinstance(result.task_id, str) or not result.task_id:
            return "result[%d].task_id_untyped" % index
        if not isinstance(result.agent_id, str) or not result.agent_id:
            return "result[%d].agent_id_untyped" % index
        if not isinstance(result.workspace, str) or not result.workspace:
            return "result[%d].workspace_untyped" % index
        if not isinstance(result.error, str):
            return "result[%d].error_untyped" % index
        attempts = result.attempts
        if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1:
            return "result[%d].attempts_untyped" % index
        if not isinstance(result.recovered, bool):
            return "result[%d].recovered_untyped" % index
    return ""


def scoping_violation(
    events: Sequence[Mapping[str, object]],
    expected_session_id: str,
    forbidden: Sequence[str],
) -> str:
    """Return "" when every event carries exactly the expected session id and
    no foreign session marker; otherwise describe the first violation."""
    for index, event in enumerate(events):
        if event.get("session_id") != expected_session_id:
            return "event[%d].session_mismatch=%s" % (index, event.get("session_id"))
        for needle in forbidden:
            if _contains_needle(event, needle):
                return "event[%d].foreign_session_marker=%s" % (index, needle)
    return ""


def _aggregate_digests(results: Sequence[AgentLaneResult]) -> list:
    """Collect the private aggregate digests a session kept in its outputs."""
    digests = []
    for result in results:
        output = result.output
        if isinstance(output, Mapping) and isinstance(output.get("aggregate_digest"), str):
            digests.append(str(output["aggregate_digest"]))
    return digests


def digest_isolation_violation(
    events: Sequence[Mapping[str, object]],
    results: Sequence[AgentLaneResult],
    audit_entries: Sequence[Mapping[str, object]],
    own_digests: Sequence[str],
    foreign_digests: Sequence[str],
) -> str:
    """Return "" when each own aggregate digest survives only inside this
    session's result outputs (never in events or audit) and no foreign
    session's digest appears anywhere in events, results, or audit;
    otherwise describe the first violation."""
    result_dicts = [dataclasses.asdict(result) for result in results]
    for index, digest_value in enumerate(own_digests):
        if not any(_contains_needle(result_dict, digest_value) for result_dict in result_dicts):
            return "own_digest[%d].missing_from_results" % index
        if _contains_needle(list(events), digest_value):
            return "own_digest[%d].leaked_to_events" % index
        if _contains_needle(list(audit_entries), digest_value):
            return "own_digest[%d].leaked_to_audit" % index
    for index, digest_value in enumerate(foreign_digests):
        for surface_name, surface in (("events", events), ("results", result_dicts), ("audit", audit_entries)):
            if _contains_needle(list(surface), digest_value):
                return "foreign_digest[%d].%s" % (index, surface_name)
    return ""


MARKER_ERROR_MAX_CHARS = 160


def marker_scope_violation(
    error_text: str,
    authorization_digest: str,
    marker_payload: Mapping[str, object],
) -> str:
    """Return "" when a commit-marker conflict surfaced a short bare error code
    that embeds no marker payload value (including the authorization digest
    the caller passed as an argument); otherwise describe the first violation.
    The caller legitimately holds the authorization digest, so its presence in
    the raised text would still mean the exception echoed private binding
    material instead of failing closed with a bare code."""
    if not error_text:
        return "empty_error_text"
    for field in sorted(str(key) for key in marker_payload.keys()):
        value = marker_payload[field]
        if isinstance(value, str) and value and value in error_text:
            return "payload_embedded=%s" % field
    if len(error_text) > MARKER_ERROR_MAX_CHARS:
        return "error_too_long=%d" % len(error_text)
    return ""


class ProtocolLeakageSuite:
    """Run protocol-boundary leakage holdouts against live parallel lanes."""

    CASE_IDS: Tuple[str, ...] = (
        "event_sink_redaction",
        "audit_error_isolation",
        "result_envelope_typing",
        "cross_session_event_scoping",
        "aggregate_digest_isolation",
        "marker_binding_scope",
    )

    def __init__(
        self,
        *,
        executor_factory: Optional[Callable[[str], SafeParallelExecutor]] = None,
        max_concurrency: int = 3,
    ):
        self.max_concurrency = max(1, min(int(max_concurrency), SafeParallelExecutor.MAX_CONCURRENCY))
        self._executor_factory = executor_factory

    def _build_executor(self, root: str) -> SafeParallelExecutor:
        if self._executor_factory is not None:
            return self._executor_factory(root)
        return SafeParallelExecutor(root, max_concurrency=self.max_concurrency)

    # ------------------------------------------------------------------
    # Case 1: event_sink_redaction
    # ------------------------------------------------------------------

    def _case_event_sink_redaction(self) -> ProtocolLeakageResult:
        output_canary = "CANARY-CALLBACK-OUTPUT-91f3"
        environment_canary = os.environ.get("NOESIS_PROTOCOL_CANARY", "") or "CANARY-ENVIRONMENT-44ac"
        with tempfile.TemporaryDirectory(prefix="noesis-proto-sink-") as root:
            boundary = str(Path(root).resolve())
            executor = self._build_executor(root)
            payloads: list[dict] = []

            def sink(event: Mapping[str, object]) -> None:
                payloads.append(dict(event))

            def callback(ctx):
                # Deliberately poison the lane output with values that must
                # never cross the event_sink boundary.
                return {
                    "canary_output": output_canary,
                    "workspace_absolute": str(ctx.workspace.resolve()),
                    "environment_value": environment_canary,
                }

            lanes = [AgentLane("sink-agent-%d" % i, "sink-task-%d" % i, "sink-ws-%d" % i) for i in range(3)]
            results = executor.execute(lanes, callback, session_id="proto-sink-redaction", event_sink=sink)
            if len(results) != len(lanes) or not all(result.status == "passed" for result in results):
                return ProtocolLeakageResult("event_sink_redaction", False, "lanes_did_not_pass")
            if len(payloads) != 2 * len(lanes):
                return ProtocolLeakageResult("event_sink_redaction", False, "unexpected_event_count=%d" % len(payloads))
            forbidden = [output_canary, environment_canary, boundary]
            forbidden.extend(result.workspace for result in results)
            violation = redaction_violation(payloads, forbidden)
            if violation:
                return ProtocolLeakageResult("event_sink_redaction", False, violation)
            if any("error" in payload for payload in payloads):
                return ProtocolLeakageResult("event_sink_redaction", False, "error_key_on_clean_lane")
            return ProtocolLeakageResult("event_sink_redaction", True, "clean:%d_events" % len(payloads))

    # ------------------------------------------------------------------
    # Case 2: audit_error_isolation
    # ------------------------------------------------------------------

    def _case_audit_error_isolation(self) -> ProtocolLeakageResult:
        victim_token = "VICTIM-AGENT-TOKEN-7e2c"
        failing_task = "audit-task-fail"
        peer_tasks = ("audit-task-alpha", "audit-task-gamma")
        with tempfile.TemporaryDirectory(prefix="noesis-proto-audit-") as root:
            executor = self._build_executor(root)

            def callback(ctx):
                if ctx.task_id == failing_task:
                    raise RuntimeError("internal cache holds peer credential " + victim_token)
                return {"completed": ctx.task_id}

            lanes = [
                AgentLane("audit-agent-alpha", peer_tasks[0], "audit-ws-alpha"),
                AgentLane("audit-agent-beta", failing_task, "audit-ws-beta"),
                AgentLane("audit-agent-gamma", peer_tasks[1], "audit-ws-gamma"),
            ]
            results = executor.execute(lanes, callback, session_id="proto-audit-isolation")
            audit_violation = ""
            if _contains_needle(list(executor.audit), victim_token):
                audit_violation = "executor_audit_contains_peer_token"
            peers = [result for result in results if result.task_id in peer_tasks]
            peer_violation = ""
            if any(_contains_needle(dataclasses.asdict(result), victim_token) for result in peers):
                peer_violation = "peer_result_contains_peer_token"
            failed = next((result for result in results if result.task_id == failing_task), None)
            if failed is None or failed.status != "failed":
                return ProtocolLeakageResult("audit_error_isolation", False, "failing_lane_not_failed")
            if victim_token not in failed.error:
                return ProtocolLeakageResult("audit_error_isolation", False, "failure_not_surfaced_to_own_lane")
            if not all(result.status == "passed" for result in peers):
                return ProtocolLeakageResult("audit_error_isolation", False, "peer_lane_degraded")
            if audit_violation or peer_violation:
                return ProtocolLeakageResult("audit_error_isolation", False, audit_violation or peer_violation)
            return ProtocolLeakageResult("audit_error_isolation", True, "audit_and_peers_clean")

    # ------------------------------------------------------------------
    # Case 3: result_envelope_typing
    # ------------------------------------------------------------------

    def _case_result_envelope_typing(self) -> ProtocolLeakageResult:
        session = "proto-envelope-session"
        ok_tasks = ("envelope-task-ok-0", "envelope-task-ok-1")
        failing_task = "envelope-task-fail"
        with tempfile.TemporaryDirectory(prefix="noesis-proto-envelope-") as root:
            executor = self._build_executor(root)

            def callback(ctx):
                if ctx.task_id == failing_task:
                    raise ValueError("typed-envelope-probe-failure")
                return {"value": 42}

            lanes = [
                AgentLane("envelope-agent-0", ok_tasks[0], "envelope-ws-0"),
                AgentLane("envelope-agent-1", ok_tasks[1], "envelope-ws-1"),
                AgentLane("envelope-agent-f", failing_task, "envelope-ws-f"),
            ]
            results = executor.execute(lanes, callback, session_id=session)
            violation = envelope_violation(results)
            if violation:
                return ProtocolLeakageResult("result_envelope_typing", False, violation)
            if any(result.session_id != session for result in results):
                return ProtocolLeakageResult("result_envelope_typing", False, "session_id_mismatch")
            passed_rows = [result for result in results if result.task_id in ok_tasks]
            if len(passed_rows) != 2 or any(result.output != {"value": 42} for result in passed_rows):
                return ProtocolLeakageResult("result_envelope_typing", False, "typed_output_not_preserved")
            failed_row = next(result for result in results if result.task_id == failing_task)
            if failed_row.error != "ValueError: typed-envelope-probe-failure":
                return ProtocolLeakageResult("result_envelope_typing", False, "typed_error_not_preserved")
            return ProtocolLeakageResult("result_envelope_typing", True, "envelope_exact:%d_results" % len(results))

    # ------------------------------------------------------------------
    # Case 4: cross_session_event_scoping
    # ------------------------------------------------------------------

    def _case_cross_session_event_scoping(self) -> ProtocolLeakageResult:
        sid_alpha = "proto-session-alpha-2c9f"
        sid_beta = "proto-session-beta-51ab"
        foreign = "proto-session-foreign-dead"
        with tempfile.TemporaryDirectory(prefix="noesis-proto-scope-") as root:
            # One shared executor, two sequential runs with distinct session ids;
            # foreign markers injected into lane data must never reach events.
            executor = self._build_executor(root)
            captured_alpha: list[dict] = []
            captured_beta: list[dict] = []

            def callback(ctx):
                return {"injected_foreign_session": foreign}

            lanes_alpha = [
                AgentLane("scope-a-agent-0", "scope-a-task-0", "scope-ws-a0"),
                AgentLane("scope-a-agent-1", "scope-a-task-1", "scope-ws-a1"),
            ]
            run_alpha = executor.execute(
                lanes_alpha,
                callback,
                session_id=sid_alpha,
                event_sink=lambda event: captured_alpha.append(dict(event)),
            )
            lanes_beta = [
                AgentLane("scope-b-agent-0", "scope-b-task-0", "scope-ws-b0"),
                AgentLane("scope-b-agent-1", "scope-b-task-1", "scope-ws-b1"),
            ]
            run_beta = executor.execute(
                lanes_beta,
                callback,
                session_id=sid_beta,
                event_sink=lambda event: captured_beta.append(dict(event)),
            )
            if not all(result.output == {"injected_foreign_session": foreign} for result in run_alpha + run_beta):
                return ProtocolLeakageResult("cross_session_event_scoping", False, "foreign_marker_not_injected")
            violation_alpha = scoping_violation(captured_alpha, sid_alpha, [foreign])
            if violation_alpha:
                return ProtocolLeakageResult("cross_session_event_scoping", False, "run_alpha:" + violation_alpha)
            violation_beta = scoping_violation(captured_beta, sid_beta, [foreign, sid_alpha])
            if violation_beta:
                return ProtocolLeakageResult("cross_session_event_scoping", False, "run_beta:" + violation_beta)
            if any(result.session_id != sid_alpha for result in run_alpha) or any(
                result.session_id != sid_beta for result in run_beta
            ):
                return ProtocolLeakageResult("cross_session_event_scoping", False, "result_session_mismatch")
            return ProtocolLeakageResult(
                "cross_session_event_scoping",
                True,
                "scoped:%d+%d_events" % (len(captured_alpha), len(captured_beta)),
            )

    # ------------------------------------------------------------------
    # Case 5: aggregate_digest_isolation
    # ------------------------------------------------------------------

    def _case_aggregate_digest_isolation(self) -> ProtocolLeakageResult:
        sid_alpha = "proto-digest-alpha-7d31"
        sid_beta = "proto-digest-beta-9e02"
        with tempfile.TemporaryDirectory(prefix="noesis-proto-digest-") as root:
            # One shared executor, two sequential runs in one process; each
            # session's callback computes a private aggregate digest kept only
            # inside its own returned outputs.
            executor = self._build_executor(root)
            captured_alpha: list[dict] = []
            captured_beta: list[dict] = []

            def make_callback(sid):
                def callback(ctx):
                    payload = {"session": sid, "task": ctx.task_id}
                    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    return {"aggregate": payload, "aggregate_digest": hashlib.sha256(encoded).hexdigest()}

                return callback

            lanes_alpha = [
                AgentLane("digest-a-agent-%d" % i, "digest-a-task-%d" % i, "digest-ws-a%d" % i) for i in range(2)
            ]
            run_alpha = executor.execute(
                lanes_alpha,
                make_callback(sid_alpha),
                session_id=sid_alpha,
                event_sink=lambda event: captured_alpha.append(dict(event)),
            )
            lanes_beta = [
                AgentLane("digest-b-agent-%d" % i, "digest-b-task-%d" % i, "digest-ws-b%d" % i) for i in range(2)
            ]
            run_beta = executor.execute(
                lanes_beta,
                make_callback(sid_beta),
                session_id=sid_beta,
                event_sink=lambda event: captured_beta.append(dict(event)),
            )
            if not all(result.status == "passed" for result in run_alpha + run_beta):
                return ProtocolLeakageResult("aggregate_digest_isolation", False, "lanes_did_not_pass")
            digests_alpha = _aggregate_digests(run_alpha)
            digests_beta = _aggregate_digests(run_beta)
            if not digests_alpha or not digests_beta:
                return ProtocolLeakageResult("aggregate_digest_isolation", False, "aggregate_digest_missing")
            if set(digests_alpha) & set(digests_beta):
                return ProtocolLeakageResult("aggregate_digest_isolation", False, "digest_collision_across_runs")
            violation_alpha = digest_isolation_violation(captured_alpha, run_alpha, executor.audit, digests_alpha, digests_beta)
            if violation_alpha:
                return ProtocolLeakageResult("aggregate_digest_isolation", False, "run_alpha:" + violation_alpha)
            violation_beta = digest_isolation_violation(captured_beta, run_beta, executor.audit, digests_beta, digests_alpha)
            if violation_beta:
                return ProtocolLeakageResult("aggregate_digest_isolation", False, "run_beta:" + violation_beta)
            return ProtocolLeakageResult(
                "aggregate_digest_isolation",
                True,
                "isolated:%d_%d_digests" % (len(digests_alpha), len(digests_beta)),
            )

    # ------------------------------------------------------------------
    # Case 6: marker_binding_scope
    # ------------------------------------------------------------------

    def _case_marker_binding_scope(self) -> ProtocolLeakageResult:
        auth_one = "AUTH-DIGEST-P1-3f5a"
        auth_two = "AUTH-DIGEST-P2-b8c7"
        with tempfile.TemporaryDirectory(prefix="noesis-proto-marker-") as root:
            path = str(Path(root) / "commit-markers.jsonl")
            ledger = WorkProductCommitMarkerLedger(path)
            marker_p1 = WorkProductCommitMarker(
                "marker-product-p1",
                "marker-task-p1",
                "marker-agent-p1",
                "marker-ws-p1",
                "marker-base-p1",
                "marker-head-p1",
                "marker-artifact-p1",
                auth_one,
            )
            first_record = ledger.record(marker_p1)
            marker_p2 = WorkProductCommitMarker(
                "marker-product-p2",
                "marker-task-p2",
                "marker-agent-p2",
                "marker-ws-p2",
                "marker-base-p2",
                "marker-head-p2",
                "marker-artifact-p2",
                auth_two,
            )
            second_record = ledger.record(marker_p2)
            if first_record.status != MARKER_STATUS_COMMITTED or second_record.status != MARKER_STATUS_COMMITTED:
                return ProtocolLeakageResult("marker_binding_scope", False, "clean_products_not_committed")
            # P2 attempt reusing the authorization digest bound to P1 while
            # carrying different product fields: identity divergence must be
            # denied fail-closed, never rewritten.
            attack = dataclasses.replace(marker_p2, authorization_digest=auth_one)
            conflict_text = ""
            raised = False
            try:
                ledger.record(attack)
            except WorkProductBenchmarkError as exc:
                raised = True
                conflict_text = str(exc)
            if not raised:
                return ProtocolLeakageResult("marker_binding_scope", False, "auth_reuse_not_rejected")
            integrity = ledger.verify_integrity()
            if not integrity.get("ok") or integrity.get("markers") != 2:
                return ProtocolLeakageResult("marker_binding_scope", False, "integrity_degraded_after_conflict")
            if ledger.count() != 2 or ledger.get("marker-product-p1") != marker_p1 or ledger.get("marker-product-p2") != marker_p2:
                return ProtocolLeakageResult("marker_binding_scope", False, "ledger_state_mutated_by_conflict")
            violation = marker_scope_violation(conflict_text, auth_one, attack.to_mapping())
            if violation:
                return ProtocolLeakageResult("marker_binding_scope", False, violation)
            reopened = WorkProductCommitMarkerLedger(path)
            if reopened.count() != 2 or not reopened.verify_integrity().get("ok"):
                return ProtocolLeakageResult("marker_binding_scope", False, "reopen_integrity_failed")
            return ProtocolLeakageResult("marker_binding_scope", True, "conflict_closed:%s" % conflict_text)

    # ------------------------------------------------------------------
    # Suite driver
    # ------------------------------------------------------------------

    def evaluate(self) -> Tuple[ProtocolLeakageResult, ...]:
        runners = (
            ("event_sink_redaction", self._case_event_sink_redaction),
            ("audit_error_isolation", self._case_audit_error_isolation),
            ("result_envelope_typing", self._case_result_envelope_typing),
            ("cross_session_event_scoping", self._case_cross_session_event_scoping),
            ("aggregate_digest_isolation", self._case_aggregate_digest_isolation),
            ("marker_binding_scope", self._case_marker_binding_scope),
        )
        outcomes: list[ProtocolLeakageResult] = []
        for case_id, runner in runners:
            try:
                outcomes.append(runner())
            except Exception as exc:  # fail closed on anything unknown
                outcomes.append(ProtocolLeakageResult(case_id, False, "unexpected_exception:" + type(exc).__name__))
        return tuple(outcomes)

    def pass_rate(self) -> float:
        results = self.evaluate()
        return sum(result.passed for result in results) / len(results) if results else 1.0

    def summary(self) -> dict:
        results = self.evaluate()
        passed = sum(1 for result in results if result.passed)
        return {
            "schema_version": PROTOCOL_LEAKAGE_SCHEMA,
            "cases": [
                {"case_id": result.case_id, "passed": result.passed, "observed": result.observed}
                for result in results
            ],
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": (passed / len(results)) if results else 1.0,
        }


__all__ = [
    "PROTOCOL_LEAKAGE_SCHEMA",
    "SINK_ALLOWED_KEYS",
    "RESULT_REQUIRED_KEYS",
    "LANE_RESULT_STATUSES",
    "MARKER_ERROR_MAX_CHARS",
    "ProtocolLeakageResult",
    "ProtocolLeakageSuite",
    "redaction_violation",
    "envelope_violation",
    "scoping_violation",
    "digest_isolation_violation",
    "marker_scope_violation",
]

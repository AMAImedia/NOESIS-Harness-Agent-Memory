# Gate 3 Recovery Evidence Status

This is the normative contract for the machine-readable recovery evidence status projection. `recovery_evidence_status` wraps the explicit startup/replay verifier without converting failures into exceptions for status consumers.

| Situation | Status | Claim |
|---|---|---|
| Completion chain and signed snapshot verify | `passed` | `true` |
| Empty event log with no completion evidence | `not_run` | `false` |
| Missing, stale, corrupt, or invalidly signed evidence | `blocked` | `false` |

The projection always includes schema version and, for blocked results, a deterministic reason. `blocked` is not equivalent to `not_run`: blocked means evidence was expected but could not be verified, while not-run means no completion evidence exists yet. The projection is read-only and never repairs the underlying event log or creates a missing snapshot.

This status vocabulary is intended for operator dashboards, evidence readiness matrices, and release reports. Consumers must not infer successful recovery from any status where `claim` is false.

## Boundary

This proves local status honesty for recovery evidence. It does not prove OS-level child-process isolation, complete artifact restoration, semantic safety, or native/external execution. Those lanes remain `not_run` or `blocked` according to their own evidence, never `passed` by implication.

Implementation: [`noesis_harness/execution_recovery.py`](../noesis_harness/execution_recovery.py). Focused coverage: [`tests/test_execution_recovery.py`](../tests/test_execution_recovery.py).

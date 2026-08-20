# Gate 3 Recovery Evidence Startup Verification

This is the normative contract for startup and replay verification of recovery evidence. `verify_recovery_evidence` audits the append-only completion-event chain and then verifies its signed durable sidecar snapshot.

An empty event log with no snapshot is a valid no-op and returns `snapshot.status=not_run` with reason `no_completion_events`. Once a completion event exists, a missing snapshot is not silently tolerated: verification fails closed with `recovery_event_snapshot_missing`. Existing snapshots must pass HMAC validation and match the current event IDs, completion receipt IDs, count, event path, and chain digest.

| Condition | Required result |
|---|---|
| Empty event log, no snapshot | Passed no-op; no recovery completion evidence is claimed. |
| Non-empty event log, valid snapshot | Passed chain and snapshot evidence. |
| Non-empty event log, missing snapshot | Fail closed with `recovery_event_snapshot_missing`. |
| Snapshot corrupt or signature-invalid | Fail closed through snapshot verification. |
| Snapshot stale against current log | Fail closed with `recovery_event_snapshot_drift`. |
| Event chain reordered or forked | Fail closed through completion-event chain audit. |

This is an explicit operator/startup gate, not an automatic repair mechanism. The verifier does not create a missing snapshot, rewrite event history, or upgrade `not_run` to `passed` without durable evidence.

## Boundary

This proves local startup/replay verification of recovery event-chain evidence. It does not prove OS-level isolation, complete artifact restoration, semantic safety, or native/external execution. Those lanes remain `not_run` until matching environments and signed operator-approved evidence are available.

Implementation: [`noesis_harness/execution_recovery.py`](../noesis_harness/execution_recovery.py). Focused coverage: [`tests/test_execution_recovery.py`](../tests/test_execution_recovery.py).

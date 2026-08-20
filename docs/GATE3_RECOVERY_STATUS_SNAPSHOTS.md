# Gate 3 Recovery Status Snapshots

This is the normative contract for the signed persistent machine-readable recovery-status snapshot. After each successful recovery completion, the executor persists the derived status projection beside the event-chain snapshot using atomic temporary-file replacement. The status payload includes schema version, event path, status, claim flag, reason, and current chain digest.

`verify_recovery_evidence_status_snapshot` reopens the sidecar, verifies its HMAC, recomputes the current status projection, and compares every bound field. A tampered signature, malformed sidecar, or changed underlying evidence fails closed rather than returning a stale status.

| Condition | Required result |
|---|---|
| Valid `passed` projection | Signed snapshot verifies with `claim=true`. |
| Valid `not_run` projection | Signed snapshot may be persisted explicitly with `claim=false`; no success is implied. |
| Valid `blocked` projection | Signed snapshot may preserve the deterministic failure reason with `claim=false`. |
| Sidecar tampering or malformed JSON | Fail closed with a status-snapshot corruption/signature error. |
| Underlying event/snapshot state changes | Fail closed with `recovery_status_snapshot_drift`. |
| Atomic write interruption | Temporary file is not treated as the canonical status snapshot. |

The status snapshot is a signed projection, not an authorization token and not a replacement for event-chain evidence. Consumers must re-verify before making a recovery claim.

## Boundary

This proves local persistence and integrity of recovery status projections. It does not prove OS-level child-process isolation, complete artifact restoration, semantic safety, or native/external execution. Those lanes remain `not_run` or `blocked` according to their own evidence.

Implementation: [`noesis_harness/execution_recovery.py`](../noesis_harness/execution_recovery.py). Focused coverage: [`tests/test_execution_recovery.py`](../tests/test_execution_recovery.py).

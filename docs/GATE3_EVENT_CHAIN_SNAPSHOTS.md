# Gate 3 Durable Recovery Event-Chain Snapshots

This is the normative contract for the signed sidecar snapshot of the recovery completion-event chain. After each successful recovery completion, the executor projects the append-only completion events, signs the canonical snapshot with the receipt-store key, and writes it through an atomic temporary-file replacement.

`verify_completion_event_snapshot` reopens the sidecar, verifies the HMAC, audits the current event chain, and compares event IDs, completion receipt IDs, count, event path, and chain digest. A snapshot is never reported as passed when the sidecar is malformed, its signature is invalid, or the current event log has drifted.

| Condition | Required result |
|---|---|
| Successful completion | Signed snapshot is atomically replaced after the completion event is appended. |
| Reopen with unchanged event log | `status=passed` with the same payload and signature. |
| Sidecar payload or signature tampering | Fail closed with `recovery_event_snapshot_signature_invalid` or `recovery_event_snapshot_corrupt`. |
| Event log reorder/corruption | Fail closed through completion-event chain audit. |
| Stale snapshot against a newer event log | Fail closed with `recovery_event_snapshot_drift`. |
| Partial temporary write | Temporary file is not treated as the canonical snapshot. |

The snapshot is a signed projection, not a replacement for the append-only event log. The implementation never repairs, truncates, reorders, or silently rebases event history.

## Boundary

This proves local durable snapshot persistence, atomic replacement, HMAC verification, and event-chain drift detection. It does not prove OS-level child-process isolation, complete rollback, semantic safety, or native/external execution. Those lanes remain `not_run` until matching environments and signed operator-approved evidence are available.

Implementation: [`noesis_harness/execution_recovery.py`](../noesis_harness/execution_recovery.py). Focused coverage: [`tests/test_execution_recovery.py`](../tests/test_execution_recovery.py).

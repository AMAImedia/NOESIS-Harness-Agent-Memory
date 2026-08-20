# Gate 3 Status Snapshot Replay Verification

This is the normative contract for exact recovery replay. A replayed recovery action is not accepted solely because its action fingerprint and committed completion receipt match. The executor must also find and verify the signed persistent recovery-status snapshot against the current event-chain evidence.

| Replay condition | Required result |
|---|---|
| Action fingerprint, completion receipt, and status snapshot all verify | Return `replayed`. |
| Same action ID with changed payload | Fail closed with `recovery_action_replay_conflict`. |
| Completion receipt missing or not committed | Fail closed with `recovery_completion_receipt_invalid`. |
| Status snapshot missing | Fail closed with `recovery_status_snapshot_missing`. |
| Status snapshot signature invalid or stale | Fail closed with the corresponding status-snapshot error. |

The replay path is idempotent only for an unchanged, fully verifiable evidence set. It never recreates missing status snapshots during replay and never returns `replayed` while the evidence projection is stale or corrupted.

## Boundary

This proves local replay/evidence binding for recovery actions. It does not prove process isolation, complete artifact restoration, semantic safety, or native/external execution. Those claims require separate evidence and remain `not_run` or `blocked` until verified.

Implementation: [`noesis_harness/execution_recovery.py`](../noesis_harness/execution_recovery.py). Focused coverage: [`tests/test_execution_recovery.py`](../tests/test_execution_recovery.py).

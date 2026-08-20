# Gate 3 Snapshot-to-Recovery Link

This is the normative contract for binding an explicit recovery action to a persisted receipt-chain snapshot. A rollback action may carry `chain_snapshot_id`; before any injected rollback handler is called, the executor reopens and verifies that snapshot and requires the target receipt ID to be a member of its ordered receipt set.

The snapshot reference is included in the deterministic action fingerprint. Therefore, changing or removing the reference under the same `action_id` is a replay conflict rather than a silent retry. A missing, malformed, stale, or unrelated snapshot fails closed before mutation.

| Condition | Required result |
|---|---|
| Valid snapshot contains target receipt | Handler may run after all existing authorization and patch checks pass. |
| Snapshot missing or corrupted | Fail closed through snapshot verification. |
| Snapshot does not contain target receipt | Fail closed with `recovery_chain_snapshot_mismatch`. |
| Same action ID with different snapshot reference | Fail closed with `recovery_action_replay_conflict`. |
| Successful rollback | Completion receipt records snapshot ID and snapshot digest. |
| Handler not injected or returns false | No recovery mutation is claimed. |

This link joins signed execution receipts, durable chain snapshots, capability-scoped recovery authorization, artifact-diff checks, and append-only completion events. It does not infer lifecycle truth from workspace names, patch IDs, or current filesystem state.

## Boundary

This proves local evidence binding between a recovery action and a persisted receipt-chain snapshot. It does not prove OS-level child-process isolation, complete rollback, semantic safety, or native/external execution. Those lanes remain `not_run` until matching environments and signed operator-approved evidence are available.

Implementation: [`noesis_harness/execution_recovery.py`](../noesis_harness/execution_recovery.py). Focused coverage: [`tests/test_execution_recovery.py`](../tests/test_execution_recovery.py).

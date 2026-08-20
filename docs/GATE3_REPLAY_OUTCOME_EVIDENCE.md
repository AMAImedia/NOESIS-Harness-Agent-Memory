# Gate 3 Replay Outcome Evidence

This is the normative contract for the machine-readable evidence returned by an exact recovery replay. A replay result includes a `noesis.recovery-replay-evidence.v1` projection that binds the action ID and action digest to the committed completion receipt and to the verified persistent recovery-status snapshot.

| Field | Meaning |
|---|---|
| `status` | `passed` only after all bound evidence verifies. |
| `claim` | `true` only for a fully verified exact replay. |
| `action_id` / `action_digest` | Identity and canonical request binding for the replayed action. |
| `completion_receipt_id` | Reference to the immutable committed recovery completion receipt. |
| `status_snapshot_digest` | Digest of the verified status snapshot payload. |

`audit_replay_outcome()` is read-only. It never creates a receipt, repairs a snapshot, applies a rollback, or converts unavailable evidence into `not_run`. Missing, stale, corrupt, or mismatched evidence fails closed. Exact replay is idempotent only when this complete evidence set remains unchanged.

After a confirmed recovery completion, the executor atomically persists a signed `noesis.recovery-replay-evidence-snapshot.v1` sidecar. Exact replay must verify this sidecar against the current action, committed receipt, and status snapshot. Missing, tampered, or drifted replay snapshots are rejected before a `replayed` result is returned.

`audit_replay_snapshot_inventory()` is a deterministic, read-only projection with schema `noesis.recovery-replay-snapshot-inventory.v1`. It records the verified sidecar path, payload digest, action identity, action digest, and completion receipt identity. Repeated audits over unchanged evidence must be byte-equivalent; verification failure is propagated fail-closed rather than producing a partial inventory.

## Boundary

This proves local replay evidence binding and deterministic reporting. It does not prove process isolation, artifact restoration completeness, semantic safety, or native/external execution. Those claims require separate matching-host and pinned-revision evidence.

Implementation: [`noesis_harness/execution_recovery.py`](../noesis_harness/execution_recovery.py). Focused coverage: [`tests/test_execution_recovery.py`](../tests/test_execution_recovery.py).

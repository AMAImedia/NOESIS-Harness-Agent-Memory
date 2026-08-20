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

`audit_replay_snapshot_inventory()` is a deterministic, read-only projection with schema `noesis.recovery-replay-snapshot-inventory.v1`. It records the verified sidecar path, payload digest, action identity, action digest, and completion receipt identity. The signed replay snapshot carries the canonical sidecar path, and verification rejects a path mismatch before inventory projection. Duplicate JSON keys are rejected as conflicting records, while mismatched action identity or completion receipt identity raises an explicit identity-conflict error. Repeated audits over unchanged evidence must be byte-equivalent; verification failure is propagated fail-closed rather than producing a partial inventory.

After a confirmed replay snapshot is written, the executor atomically persists a signed `noesis.recovery-replay-snapshot-inventory-snapshot.v1` sidecar. Exact replay verifies this durable inventory snapshot against the current replay snapshot before returning `replayed`. Missing, corrupt, path-mismatched, tampered, or drifted inventory snapshots fail closed; no inventory snapshot is silently recreated during replay.

Replay and inventory sidecars are action-scoped and use a deterministic digest of `action_id` in their filenames. The recovery-status projection used by replay is also action-scoped, so two completed actions on one append-only event log cannot overwrite each other’s replay evidence or status evidence. Global operator status remains available as a separate aggregate snapshot.

`audit_replay_evidence_catalog()` is a read-only projection with schema `noesis.recovery-replay-evidence-catalog.v1`. It enumerates all action-scoped inventory sidecars, verifies their signatures and paths, binds each record to its replay snapshot, action event, committed completion receipt, and action-scoped status snapshot, and returns a deterministic catalog digest. Missing, duplicate, stale, path-conflicting, signature-invalid, or identity-conflicting records fail closed. Exact replay runs this catalog audit before returning `replayed`.

After catalog verification, the executor atomically persists a signed global `noesis.recovery-replay-evidence-catalog-snapshot.v1` sidecar. Exact replay verifies this durable aggregate snapshot against the current catalog. Missing, corrupt, path-mismatched, tampered, or drifted catalog snapshots block replay and are never silently recreated during replay.

The final write is a signed `noesis.recovery-replay-evidence-commit-manifest.v1` for each action. It binds the action, committed completion receipt, action-scoped status/replay/inventory snapshots, the global catalog snapshot, and a stable per-action completeness-record digest. The implementation may write a provisional manifest while a new action is being added, then refreshes the completeness snapshot and atomically rewrites the manifest as the final durable write. Exact replay verifies this final manifest last, so a partial evidence bundle cannot be promoted to `replayed`; missing, corrupt, path-mismatched, tampered, or drifted manifests fail closed without repair.

`audit_replay_evidence_completeness()` is a read-only startup-style audit with schema `noesis.recovery-replay-evidence-completeness.v1`. It requires one valid action-scoped commit manifest for every completed recovery event, validates receipt identity and manifest paths, and requires manifest count to equal both event count and catalog count. Any missing, duplicate, corrupt, conflicting, or uncommitted completion blocks the completeness claim. The audit independently recomputes each signed manifest `bundle_digest` before accepting count parity, so startup completeness cannot bypass whole-bundle tamper detection.

The completeness projection is also persisted as signed `noesis.recovery-replay-evidence-completeness-snapshot.v1`. Exact replay verifies this durable claim against the current bundle after the commit manifest gate. Missing, corrupt, path-mismatched, tampered, or drifted completeness snapshots fail closed and are never silently recreated during replay.

Before any replay evidence is promoted to `replayed`, the executor verifies the signed `noesis.recovery-event-chain-snapshot.v1` against the append-only completion event log. This check precedes action-scoped status verification so missing or drifted chain evidence reports the chain denial directly. Duplicate JSON keys in the chain snapshot are rejected.

The action replay projection also audits the target action’s completion-event prefix and requires its final committed receipt ID to equal the replay record’s completion receipt ID. The resulting `event_chain_digest` is included in the signed replay evidence snapshot, preventing an action from being replayed against a different committed completion event.

The final commit manifest additionally carries a deterministic `bundle_digest` over its canonical action-scoped fields. Verification recomputes this digest before accepting the manifest, binding the status, replay, inventory, catalog, completeness, receipt, and path projections as one evidence bundle.

## Boundary

This proves local replay evidence binding and deterministic reporting. It does not prove process isolation, artifact restoration completeness, semantic safety, or native/external execution. Those claims require separate matching-host and pinned-revision evidence.

Implementation: [`noesis_harness/execution_recovery.py`](../noesis_harness/execution_recovery.py). Focused coverage: [`tests/test_execution_recovery.py`](../tests/test_execution_recovery.py).

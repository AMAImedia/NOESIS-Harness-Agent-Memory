# Gate 3 Recovery Completion-Event Chain

This is the normative contract for the append-only recovery completion-event chain. Every newly emitted `execution_recovery_completed` event carries `previous_event_digest`. The first event references `genesis`; each later event references the digest of the previous completion payload. The audit walks completion events in append order, verifies unique action IDs, linked digests, and referenced committed completion receipts.

| Condition | Required result |
|---|---|
| Valid event chain | `status=passed`, count, event IDs, completion receipt IDs, and final chain digest. |
| Reordered completion events | Fail closed with `recovery_completion_event_chain_mismatch`. |
| Duplicate action ID/fork | Fail closed with `recovery_completion_event_fork`. |
| Malformed completion payload | Fail closed with `recovery_completion_event_corrupt`. |
| Missing or invalid completion receipt | Fail closed with `recovery_completion_receipt_invalid`. |
| Non-completion events | Ignored by this projection; they do not alter the completion chain head. |

The chain audit is a read-only projection over the append-only event log. It does not repair, reorder, or delete events. A legacy completion event without `previous_event_digest` may remain readable through compatibility paths, but it is not valid new chain evidence.

## Boundary

This proves local ordering and receipt linkage for recovery completion events. It does not prove OS-level child-process isolation, complete rollback, semantic safety, or native/external execution. Those lanes remain `not_run` until matching environments and signed operator-approved evidence are available.

Implementation: [`noesis_harness/execution_recovery.py`](../noesis_harness/execution_recovery.py). Focused coverage: [`tests/test_execution_recovery.py`](../tests/test_execution_recovery.py).

# Gate 3 Durable Receipt Chain

This is the normative contract for verifying an ordered receipt chain after durable-store reopen. `ExecutionReceiptStore.audit_chain` loads the requested receipt IDs from SQLite/WAL storage, verifies each stored receipt, preserves caller-provided order, and delegates to the immutable chain validator.

| Condition | Required result |
|---|---|
| Valid stored chain after reopen | `status=passed`, count, first/last IDs, and deterministic chain digest. |
| Reversed or reordered IDs | Fail closed when adjacent lifecycle transitions become invalid. |
| Missing stored entry | Fail closed with `receipt_chain_missing`; no partial passed evidence. |
| Stored payload tampering | Fail closed through receipt signature/digest verification. |
| Duplicate chain entry | Fail closed through duplicate receipt-ID detection. |
| Store reopen | The same ordered IDs produce the same chain result and digest. |

The chain IDs are an explicit ordered evidence input rather than an inferred SQL row order. This avoids silently converting storage order, insertion timing, or a partial query into lifecycle truth. The durable store remains append-only; audit never mutates receipts or repairs missing chain entries.

## Boundary

This proves local SQLite/WAL persistence and ordered receipt evidence across reopen. It does not prove native OS isolation, complete artifact restoration, semantic safety, or external/native execution. Those lanes remain `not_run` until matching environments and signed operator-approved evidence are available.

Implementation: [`noesis_harness/execution_assurance.py`](../noesis_harness/execution_assurance.py). Focused coverage: [`tests/test_execution_assurance.py`](../tests/test_execution_assurance.py).

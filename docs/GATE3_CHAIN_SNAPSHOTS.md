# Gate 3 Persistent Receipt-Chain Snapshots

This is the normative contract for storing and reopening durable receipt-chain evidence. `ExecutionReceiptStore.save_chain_snapshot` first validates an ordered chain, derives a deterministic snapshot ID from the ordered receipt IDs and chain digest, and persists the snapshot idempotently in SQLite/WAL storage.

`get_chain_snapshot` verifies the stored snapshot payload, recomputes its snapshot digest, reloads the referenced receipts, and compares the current chain digest with the persisted value. A snapshot is never reported as passed when its payload is malformed, its reference is missing, or the current receipt chain has drifted.

| Condition | Required result |
|---|---|
| First valid save | Persists one deterministic snapshot and returns `status=passed`. |
| Exact repeated save | Returns the identical snapshot without duplicate rows or mutation. |
| Database reopen | The same snapshot ID reopens and verifies against current receipts. |
| Snapshot payload corruption | Fail closed with `receipt_chain_snapshot_tampered`. |
| Missing snapshot | Fail closed with `receipt_chain_snapshot_missing`. |
| Missing referenced receipt | Fail closed through the durable chain loader. |
| Current chain digest drift | Fail closed with `receipt_chain_snapshot_drift`. |

The snapshot is evidence about a specific ordered receipt set, not a replacement for the underlying receipts. Storage remains append-only; the snapshot API never repairs, rewrites, or silently rebinds missing or changed references.

## Boundary

This proves local persistence and reopen verification of receipt-chain evidence. It does not prove OS-level child-process isolation, complete rollback, semantic safety, or native/external execution. Those lanes remain `not_run` until matching environments and signed operator-approved evidence are available.

Implementation: [`noesis_harness/execution_assurance.py`](../noesis_harness/execution_assurance.py). Focused coverage: [`tests/test_execution_assurance.py`](../tests/test_execution_assurance.py).

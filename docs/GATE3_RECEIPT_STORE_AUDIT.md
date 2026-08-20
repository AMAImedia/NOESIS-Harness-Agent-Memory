# Gate 3 Receipt Store Audit

This is the normative contract for auditing the durable execution receipt store. The audit loads every stored payload in deterministic `receipt_id` order, reconstructs each receipt, verifies its schema, digest, HMAC signature, and database identity binding, and returns a stable integrity snapshot.

| Condition | Required result |
|---|---|
| All stored receipts valid | `status=passed`, count, sorted receipt IDs, and aggregate payload digest are returned. |
| Exact database reopen | The same receipt set produces the same audit snapshot and aggregate digest. |
| Malformed JSON or missing fields | Fail closed with `stored_receipt_tampered`. |
| Invalid digest or HMAC | Fail closed with `stored_receipt_tampered`. |
| Row key differs from receipt ID | Fail closed with `stored_receipt_identity_mismatch`. |
| Duplicate `put` with identical payload | No-op; the existing receipt is returned. |
| Duplicate `put` with different payload | Fail closed with `receipt_conflict`. |

The audit is local evidence of receipt-store integrity. It does not prove that a child process was isolated, that artifact restoration occurred, or that external/native execution is available. Those lanes remain separately classified as `not_run` until their required environments and signed evidence exist.

Implementation: [`noesis_harness/execution_assurance.py`](../noesis_harness/execution_assurance.py). Focused coverage: [`tests/test_execution_assurance.py`](../tests/test_execution_assurance.py).

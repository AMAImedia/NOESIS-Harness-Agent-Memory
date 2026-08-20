# Gate 3 Receipt Chain Audit

This is the normative contract for validating an ordered immutable execution-receipt history. The chain validator verifies every receipt, rejects duplicate receipt IDs, validates each adjacent lifecycle transition, and returns a deterministic chain digest.

## Chain rules

| Condition | Required result |
|---|---|
| Valid ordered history | `status=passed`, count, first/last receipt IDs, and chain digest. |
| Lifecycle gap | Fail closed; for example, `prepared → rolled_back` is invalid. |
| Reordering | Fail closed when adjacent outcomes no longer form an allowed transition. |
| Fork/duplicate | Fail closed on repeated receipt IDs. |
| Signature or field tampering | Fail closed before chain evidence is emitted. |
| Empty or non-tuple history | Fail closed with `receipt_chain_required`. |

The chain is append-only and does not mutate any receipt. Its digest covers the ordered receipt ID, outcome, and receipt digest of every entry. This provides a stable local evidence summary while preserving the stronger individual receipt, artifact-diff, recovery, and terminal lifecycle checks.

## Boundary

Receipt-chain validation proves local evidence ordering and integrity only. It does not prove operating-system isolation, complete artifact restoration, semantic safety, or native/external execution availability. Windows/macOS and Hermes/OpenCode/DeepSeek Harness lanes remain `not_run` until matching environments and signed operator-approved evidence are available.

Implementation: [`noesis_harness/execution_assurance.py`](../noesis_harness/execution_assurance.py). Focused coverage: [`tests/test_execution_assurance.py`](../tests/test_execution_assurance.py).

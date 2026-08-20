# Gate 3 Recovery Replay Assurance

This is the normative contract for explicit child-runtime recovery after signed artifact-diff receipts. Recovery is **authenticated, receipt-linked, artifact-aware, idempotent, and honest about rollback**.

## Recovery action binding

A recovery action binds an action ID, operation, run ID, receipt ID, patch proposal, workspace, current base snapshot, operator identity, session identity, scope, and optional `artifact_diff_digest`. The complete action mapping is fingerprinted before execution. If an already-completed action ID is replayed with a different payload, recovery fails closed with a replay conflict rather than treating the request as an idempotent duplicate.

For rollback, the stored receipt must be signed and recoverable, the recovery ledger must point to that receipt, the patch must be approved for the requested workspace and fresh base snapshot, and an optional action diff digest must match the receipt's bound artifact diff digest. A stale receipt, workspace mismatch, stale base, unapproved patch, or artifact-diff mismatch is rejected before the injected handler is called.

| Outcome | Meaning |
|---|---|
| `replayed` | The exact same authenticated action and fingerprint were already completed; no handler is called again. |
| `recovered` | An interrupted run was explicitly resumed and the handler confirmed the transition. |
| `rolled_back` | The handler confirmed rollback and the recovery ledger marked the run rolled back. |
| rejected | Authorization, receipt, patch, freshness, digest, or handler confirmation failed; no success evidence is emitted. |

The system never claims that rollback or restoration occurred merely because an action was accepted. The injected handler must return true, and the durable recovery state and append-only completion event are written only after that confirmation.

## Boundary

This contract proves local evidence linkage and bounded recovery state transitions. It does not prove that a handler restored every byte, that the operating system isolated the child, or that generated content is semantically safe. Native Windows/macOS and external Hermes/OpenCode/DeepSeek Harness recovery runs remain `not_run` until matching hosts, exact pinned revisions, disposable environments, and signed operator-approved evidence exist.

## Implementation and evidence

The implementation is [`noesis_harness/execution_recovery.py`](../noesis_harness/execution_recovery.py) and depends on [`noesis_harness/execution_assurance.py`](../noesis_harness/execution_assurance.py). Focused adversarial coverage is in [`tests/test_execution_recovery.py`](../tests/test_execution_recovery.py), including stale base, missing approval, stale artifact diff, duplicate exact replay, changed-payload replay conflict, authentication denial, and handler-confirmation requirements.

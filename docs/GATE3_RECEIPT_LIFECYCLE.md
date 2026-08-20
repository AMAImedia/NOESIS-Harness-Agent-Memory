# Gate 3 Receipt Lifecycle Transitions

This is the normative contract for immutable execution receipt lifecycle transitions. Receipt history is append-only: a new receipt may describe a permitted state transition, but an existing receipt is never mutated.

## Allowed transitions

| Previous outcome | Allowed next outcomes |
|---|---|
| `prepared` | `committed`, `rejected`, `failed`, `timed_out` |
| `committed` | `rolled_back` |
| `failed` | `rolled_back` |
| `timed_out` | `rolled_back` |
| `rejected` | None |
| `rolled_back` | None |

The transition validator also requires the same request digest, policy digest, workspace-before digest, and artifact-diff digest. The exact same receipt object is an immutable idempotent no-op. A different request, policy, workspace, artifact binding, or unsupported outcome transition fails closed.

This contract complements the durable receipt-store audit, signed receipt verification, artifact-diff binding, terminal recovery lifecycle, and explicit rollback-handler confirmation. It prevents a valid receipt from being reused as evidence for a different request or artifact state.

## Boundary

This validator proves only local receipt-history consistency. It does not prove that a child process was isolated by the operating system, that rollback restored every artifact, or that external/native execution is available. Those claims remain `not_run` until their environments and signed operator-approved evidence are present.

Implementation: [`noesis_harness/execution_assurance.py`](../noesis_harness/execution_assurance.py). Focused coverage: [`tests/test_execution_assurance.py`](../tests/test_execution_assurance.py).

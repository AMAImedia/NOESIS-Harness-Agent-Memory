# Gate 3 Terminal Lifecycle Assurance

This is the normative contract for terminalizing child-runtime execution runs in the durable recovery ledger. A run may transition from `running` to exactly one terminal outcome: `completed`, `failed`, `timed_out`, or `denied`.

## Idempotent completion

An exact duplicate terminal completion is a no-op that returns the existing durable record. A completion that attempts to change the terminal status, post-run workspace digest, or receipt ID is rejected with `execution_run_terminal_conflict`. The update is guarded by the `running` state so a retry cannot overwrite a terminal record after a crash or concurrent completion.

| Case | Result |
|---|---|
| First completion of a running run | Writes one terminal state, workspace-after digest, receipt ID, and update timestamp. |
| Exact duplicate completion | Returns the existing terminal record without mutation. |
| Different terminal payload | Fails closed with `execution_run_terminal_conflict`. |
| Unknown run | Fails closed with `execution_run_not_found`. |
| Unsupported terminal status | Fails closed with `invalid_recovery_terminal_status`. |

This lifecycle guard complements signed receipt storage, artifact-diff binding, request identity replay denial, recovery action fingerprints, and explicit rollback-handler confirmation. It does not claim that a child process was isolated by the operating system or that a handler restored every artifact byte.

## Implementation and evidence

The implementation is [`noesis_harness/execution_assurance.py`](../noesis_harness/execution_assurance.py). Focused coverage is in [`tests/test_execution_assurance.py`](../tests/test_execution_assurance.py), with related child-runtime and recovery tests. Native Windows/macOS and external Hermes/OpenCode/DeepSeek Harness execution remain `not_run` until matching hosts, exact pinned revisions, disposable environments, and signed operator-approved evidence are available.

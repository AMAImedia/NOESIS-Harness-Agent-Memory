# Gate 3 Recovery Completion Receipts

This is the normative contract for recovery completion evidence. After an injected recovery handler confirms the mutation and the recovery store records the terminal state, the executor creates and persists a signed execution receipt with `outcome=committed` and a recovery-specific side-effect marker.

The completion receipt binds the recovery action mapping, run ID, policy scope, operator identity, optional chain snapshot reference, workspace state, and artifact-diff digest. The append-only completion event records the completion receipt ID. On exact replay, the executor verifies that the referenced completion receipt still exists and remains a valid committed receipt before returning `replayed`.

| Condition | Required result |
|---|---|
| Handler confirms and state transition succeeds | Persist signed completion receipt, then append event containing its ID. |
| Handler missing or returns false | No committed completion receipt or successful recovery claim. |
| Exact replay with valid completion receipt | Return `replayed` and existing event result. |
| Event completion-receipt reference tampered | Fail closed with `recovery_completion_receipt_invalid`. |
| Changed action payload under same action ID | Fail closed with `recovery_action_replay_conflict`. |
| Completion receipt payload/signature tampered | Fail closed through receipt-store verification. |

This contract makes recovery success auditable without treating an event-log line alone as proof. Existing legacy events without a completion receipt reference remain readable for compatibility, but newly generated recovery completions always include the signed receipt reference.

## Boundary

This proves local signed completion evidence and replay verification. It does not prove OS-level isolation, complete artifact restoration, semantic safety, or native/external execution. Those lanes remain `not_run` until matching environments and signed operator-approved evidence are available.

Implementation: [`noesis_harness/execution_recovery.py`](../noesis_harness/execution_recovery.py). Focused coverage: [`tests/test_execution_recovery.py`](../tests/test_execution_recovery.py).

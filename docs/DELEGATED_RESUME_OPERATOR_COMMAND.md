# Operator-Owned Delegated Resume Command

## Purpose

The operator resume command is the only control-plane path that may authorize a delegated continuation. Telemetry, snapshots, and SSE remain read-only and cannot trigger resume.

## Contract

The command uses `noesis.delegated-resume-action.v1` and binds `action_id`, `operator_id`, `session_id`, `task_id`, `approval_id`, and the immutable request digest into an HMAC-SHA256 signature. The authenticated operator must match `operator_id` and hold the `task:resume` scope.

| Guard | Failure behavior |
|---|---|
| Missing handler or operator context | HTTP `405`/`403`; no callback. |
| Invalid schema or signature | Rejected before callback. |
| Wrong operator or missing `task:resume` scope | Rejected before callback. |
| Reused `action_id` | Returns durable `replayed` result; callback is not repeated. |
| Stale or reused delegated approval | The underlying `DelegatedResumeStore` rejects it. |
| Callback failure | Signed `rejected` receipt is appended; failure is not converted into success. |

The authenticated endpoint is `POST /api/delegated-resume`. It accepts only the signed command object and returns a bounded action summary plus redacted result metadata. The executor appends `noesis.delegated-resume-receipt.v1` to an append-only audit log. The receipt is signed and binds the action, operator, session, task, status, and result digest.

## Non-automation boundary

This command is operator-owned, not autonomous. No background process polls it, telemetry cannot invoke it, and the endpoint does not manufacture approval IDs. The caller must supply a fresh approval produced by the delegated resume lifecycle. The reusable `bridge_runtime_resume_callback()` wiring binds the signed action to `TaskExecutionBridge.resume_delegated_runtime()`. The complete path is therefore: signed command validation, fresh approval consumption, task state recovery, Actions claim, workspace binding, child-runtime execution, signed receipt verification, and only then operator audit receipt creation. Existing Actions claim, workspace binding, sandbox, child-runtime and execution-receipt guards remain mandatory.

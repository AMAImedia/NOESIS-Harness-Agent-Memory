# Delegated Task Resume and Replay Contract

## Purpose

Delegated child work must survive interruption without silently rerunning an old request. This contract binds every delegation to immutable session, task, agent, workspace, capability, and request identity metadata.

| State | Meaning | Resume behavior |
|---|---|---|
| `created` / `checkpointed` | Delegation exists and may emit durable checkpoints. | Normal execution may proceed under its original approval boundary. |
| `interrupted` / `failed` | Child work stopped before a terminal result. | Resume requires a fresh operator approval bound to the latest checkpoint. |
| `resume_approved` / `resuming` | A fresh approval exists or has been consumed. | The approval is single-use; request identity must match exactly. |
| `completed` / `cancelled` | Terminal state. | No checkpoint or replay is allowed. |

## Invariants

The append-only `DelegatedResumeStore` never executes a child process. It records identity and lifecycle evidence only. A resume approval is derived from the delegation identity, approval token digest, and latest checkpoint digest. Changing the workspace, capabilities, agent, task, session, or any other request identity causes `delegation_request_mutated` and is rejected.

After an approval is consumed, a second attempt is rejected as `resume_approval_replayed`. If a checkpoint changes after approval, the approval becomes stale and is rejected as `resume_checkpoint_drift`. Terminal delegations cannot accept late checkpoints or resume approvals.

> A resume record is authorization to attempt one approved continuation, not permission to replay an arbitrary historical command.

## Evidence boundary

The store provides durable state and deterministic replay guards for integration by `TaskExecutionBridge` and `ChildExecutionRuntime`. `TaskExecutionBridge.resume_delegated()` consumes the single-use approval before moving a failed task back through `planned` to `waiting_approval`; it then reuses the normal Actions claim, workspace binding, child runtime, and receipt verification gates. A missing or replayed approval stops before the callback can start.

The store does not itself grant capabilities, bypass sandbox policy, invoke providers, or activate executable skills. Those actions remain subject to the existing Trust Plane, Child Execution Runtime, sandbox backend, Actions claim, and operator approval contracts. HealthServer exposes only bounded read-only resume status with `automatic_resume=false`; telemetry is not a control action.

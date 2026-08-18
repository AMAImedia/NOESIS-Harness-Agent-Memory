# Learning Promotion Integration Contract

This contract connects terminal task outcomes from the durable task/session event stream to the human-governed learning promotion pipeline without enabling automatic skill activation.

## Integration surfaces

| Surface | Contract |
|---|---|
| Durable event stream | `PromotionEventBridge` replays append-only `task_state_changed` events. Only `committed` and `failed` states are eligible for capture; `cancelled` is explicitly denied. |
| Terminal mapping | `committed` becomes a successful promotion outcome; `failed` becomes a failure outcome. Active, review, planned and unknown states are ignored by the bridge. |
| Policy simulation | `OwnershipPolicySimulator` derives the decision from authoritative task/session metadata and an explicit runtime owner lookup; it delegates deterministic digest construction to `RuntimePolicySimulator`. It performs no side effects. Session mismatch, missing owner, denied scope, malformed metadata and lookup errors fail closed. |
| Durable checkpoints | The bridge writes `started`, `completed` and `denied` checkpoint events keyed by source task event ID. Completed and denied events are not replayed. Existing receipts are reused by experience ID to absorb safe retries. |
| Evaluator registry | Evaluator versions must be registered explicitly and uniquely. Unknown or duplicate versions fail closed. Evaluators provide deterministic holdout cases; they do not promote anything. |
| Promotion operations | Capture, evaluate, propose, approve, promote and rollback are explicit method calls. `TaskExecutionBridge.poll_promotion_events(operator_trigger=True)` is the only lifecycle entry point for bridge polling; `execute()` never polls or promotes implicitly. |
| Operator approval UI | `PromotionApprovalAction` is a versioned non-secret action envelope for `approve`, `reject` and `rollback`. `PromotionActionExecutor` applies only explicit proposal operations, requires an independent reviewer, signs a receipt and stores an idempotent action record. Optional authenticated `POST /api/promotion-actions` validates the envelope and passes it to an injected handler; the HealthServer never performs promotion itself. |
| Operator telemetry | Lifecycle and denial events are bounded, redacted and exposed under the optional `learning_promotion` section of the read-only HealthServer telemetry snapshot and existing SSE snapshot. |
| Activation | Integration defaults `activate=False`; active skill pointers cannot be created by task completion, policy simulation, UI action validation, approval action execution or evaluation. |

## Event boundary

The integration emits `experience_captured`, `holdout_evaluated`, `promotion_proposed`, `promotion_approved`, `promotion_completed`, `promotion_rolled_back` and `promotion_blocked`. Telemetry contains identifiers, states, counts, digests and bounded denial reasons only. Content-like fields, credentials and API keys are recursively redacted.

## Recovery and retry semantics

The bridge is replay-safe for a repeated poll and a newly constructed bridge using the same checkpoint path. A source event with a completed or denied checkpoint is skipped. A started checkpoint without a terminal checkpoint may be retried; receipt lookup by experience ID prevents duplicate capture after a crash between capture and checkpoint append.

Operator actions are separately replay-safe by `action_id`. A completed action returns its stored signed receipt instead of reapplying the state transition. Approval requires an independent reviewer relative to the experience owner. `reject` is allowed only from `review`; `rollback` is allowed only from `promoted` and does not activate anything. Promotion approval and activation remain outside task-event replay and are never inferred from a checkpoint.

## Non-goals

This layer does not execute skill content, choose an evaluator implicitly, activate a skill automatically, or claim general autonomous learning. It is a governed bridge to the existing promotion state machine. Runtime activation remains a separate capability-gated implementation task.

Implementation: `noesis_harness/promotion_integration.py`; lifecycle wiring: `noesis_harness/execution_bridge.py`; HTTP contract: `noesis_harness/health_server.py`; task source: `noesis_harness/task_session_api.py`; HealthServer injection: `promotion_telemetry=`; tests: `tests/test_promotion_integration.py`, `tests/test_execution_bridge.py` and `tests/test_ui_contract_health.py`.

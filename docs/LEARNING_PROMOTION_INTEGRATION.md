# Learning Promotion Integration Contract

This contract connects terminal task outcomes from the durable task/session event stream to the human-governed learning promotion pipeline without enabling automatic skill activation.

## Integration surfaces

| Surface | Contract |
|---|---|
| Durable event stream | `PromotionEventBridge` replays append-only `task_state_changed` events. Only `committed` and `failed` states are eligible for capture; `cancelled` is explicitly denied. |
| Terminal mapping | `committed` becomes a successful promotion outcome; `failed` becomes a failure outcome. Active, review, planned and unknown states are ignored by the bridge. |
| Policy simulation | A caller-supplied simulator must return `PolicySimulation` or an equivalent mapping. It must explicitly allow the event and provide source digest, policy digest, agent identity and scope. Missing fields, malformed responses and simulator exceptions fail closed. |
| Durable checkpoints | The bridge writes `started`, `completed` and `denied` checkpoint events keyed by source task event ID. Completed and denied events are not replayed. Existing receipts are reused by experience ID to absorb safe retries. |
| Evaluator registry | Evaluator versions must be registered explicitly and uniquely. Unknown or duplicate versions fail closed. Evaluators provide deterministic holdout cases; they do not promote anything. |
| Promotion operations | Capture, evaluate, propose, approve, promote and rollback are explicit method calls. No background promotion is started by task completion. |
| Operator telemetry | Lifecycle and denial events are bounded, redacted and exposed under the optional `learning_promotion` section of the read-only HealthServer telemetry snapshot and existing SSE snapshot. |
| Activation | Integration defaults `activate=False`; active skill pointers cannot be created by task completion, policy simulation or evaluation. |

## Event boundary

The integration emits `experience_captured`, `holdout_evaluated`, `promotion_proposed`, `promotion_approved`, `promotion_completed`, `promotion_rolled_back` and `promotion_blocked`. Telemetry contains identifiers, states, counts, digests and bounded denial reasons only. Content-like fields, credentials and API keys are recursively redacted.

## Recovery and retry semantics

The bridge is replay-safe for a repeated poll and a newly constructed bridge using the same checkpoint path. A source event with a completed or denied checkpoint is skipped. A started checkpoint without a terminal checkpoint may be retried; receipt lookup by experience ID prevents duplicate capture after a crash between capture and checkpoint append. Promotion approval and activation remain outside replay and are never inferred from a checkpoint.

## Non-goals

This layer does not execute skill content, choose an evaluator implicitly, activate a skill automatically, or claim general autonomous learning. It is a governed bridge to the existing promotion state machine. Runtime activation remains a separate capability-gated implementation task.

Implementation: `noesis_harness/promotion_integration.py`; task source: `noesis_harness/task_session_api.py`; HealthServer injection: `promotion_telemetry=`; tests: `tests/test_promotion_integration.py`.

# Learning Promotion Integration Contract

This contract connects terminal task outcomes to the human-governed learning promotion pipeline without enabling automatic skill activation.

## Integration surfaces

| Surface | Contract |
|---|---|
| Task completion | Only terminal task states (`done`, `completed`, `success`, `failed`) may create an experience receipt. Active or unknown tasks are rejected. |
| Evaluator registry | Evaluator versions must be registered explicitly and uniquely. Unknown or duplicate versions fail closed. Evaluators provide deterministic holdout cases; they do not promote anything. |
| Promotion operations | Capture, evaluate, propose, approve, promote and rollback are explicit method calls. No background promotion is started by task completion. |
| Operator telemetry | Lifecycle events are bounded, redacted and exposed under the optional `learning_promotion` section of the read-only HealthServer telemetry snapshot and existing SSE snapshot. |
| Activation | Integration defaults `activate=False`; active skill pointers cannot be created by task completion or evaluation. |

## Event boundary

The integration emits `experience_captured`, `holdout_evaluated`, `promotion_proposed`, `promotion_approved`, `promotion_completed`, and `promotion_rolled_back`. Telemetry contains identifiers, states, counts and digests only. Content-like fields, credentials and API keys are recursively redacted.

## Non-goals

This layer does not execute skill content, choose an evaluator implicitly, activate a skill automatically, or claim general learning capability. It is a governed bridge to the existing promotion state machine. Runtime activation remains a separate capability-gated implementation task.

Implementation: `noesis_harness/promotion_integration.py`; HealthServer injection: `promotion_telemetry=`; tests: `tests/test_promotion_integration.py`.

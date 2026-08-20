# Bounded AgentLoop Conformance

`noesis_harness.agent_loop.AgentLoop` implements the local observe → pack → lease → act → judge → writeback cycle. The action callback is injected; the core loop does not call an LLM, provider, network, or external harness.

| Stop condition | Result | Safety meaning |
|---|---|---|
| Passing action reports `done` | `done` | Lease is released after validated completion. |
| Maximum turn count reached | `max_turns` | The loop is bounded and cannot run indefinitely. |
| Invalid action callback | `act_invalid` | Preflight rejects non-callable action before lease acquisition. |
| Lease unavailable | `blocked` | No action callback is invoked without ownership. |
| Lease acquire exception | `lease_error` | Ownership dependency failure is bounded before action. |
| Malformed lease response | `lease_shape_error` | Invalid ownership response stops before action. |
| Loop guard rejection | `loop` | Repeated action fingerprint stops the cycle before action. |
| Context pack failure | `context_over` | The cycle stops instead of exceeding its budget. |
| Pack exception | `pack_error` | Dependency failure is bounded to a result and the lease is released. |
| Malformed pack response | `pack_shape_error` | Invalid pack response is rejected and the lease is released. |
| Guard exception | `guard_error` | Dependency failure is bounded to a result and the lease is released. |
| Malformed guard response | `guard_shape_error` | Invalid guard response is rejected and the lease is released. |
| Malformed action result | `result_shape_error` | Non-mapping output is rejected before judge or writeback. |
| Judge failure | `judge_fail` | Failed output is not promoted as successful work. |
| Action exception | `act_error` | The exception is bounded to a result and the lease is released. |
| Judge exception | `judge_error` | The exception is bounded to a result and the lease is released. |
| Malformed judge result | `judge_shape_error` | Non-mapping verdict is rejected and the lease is released. |
| Memory write exception | `memory_error` | Failed writeback is bounded to a result and the lease is released. |
| Budget exception | `budget_error` | Budget failures are bounded to a result and the lease is released. |
| Malformed budget response | `budget_shape_error` | Invalid budget response is rejected and the lease is released. |
| Clock exception | `clock_error` | Receipt timestamp failure is bounded and the lease is released. |
| Lease renewal exception | `lease_renew_error` | Renewal failure is bounded to a result and the lease is released. |
| Budget exhaustion | `budget` | Further turns are denied after the bounded budget is consumed. |

The constructor rejects non-positive or non-integer `max_turns`, rejects a non-callable injected clock, and rejects missing required dependency methods before any lease can be acquired. Optional budget and event sinks are validated when provided.
 A callable clock is preserved even when its boolean value is false.
 Action and judge outputs must be mappings; malformed outputs are bounded as failures. Budget authorization occurs before memory writeback. Memory writeback occurs only when the judge returns `pass=true` and the budget manager accepts the turn; rejected or budget-denied candidates are not persisted.
 Telemetry append failures are isolated and do not convert a valid control result into an execution failure.
 The loop may write memory only after an action result is returned; promotion remains governed by the separate human-approval and evidence contracts.
 This is a local control-plane loop, not proof of autonomous external Hermes execution or self-learning without approval.

LoopGuard rejects invalid non-positive bounds before execution and canonicalizes mapping actions before fingerprinting, so key order does not change repeat detection. Every post-acquisition early stop releases the lease, including context-pack failure, pack exception, loop-guard rejection, guard exception, action exception, judge exception, memory write exception, budget exception, and lease renewal exception.
 Turn timestamps use an injectable clock so evidence tests can remain deterministic. The current conformance tests cover bounded turns, lease-miss action suppression, loop-guard stop, cleanup on failures, exception containment, deterministic timestamps, and judge-gated completion. External provider lanes remain disabled unless an operator supplies pinned environments and signed receipts.

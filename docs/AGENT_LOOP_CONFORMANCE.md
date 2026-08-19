# Bounded AgentLoop Conformance

`noesis_harness.agent_loop.AgentLoop` implements the local observe → pack → lease → act → judge → writeback cycle. The action callback is injected; the core loop does not call an LLM, provider, network, or external harness.

| Stop condition | Result | Safety meaning |
|---|---|---|
| Passing action reports `done` | `done` | Lease is released after validated completion. |
| Maximum turn count reached | `max_turns` | The loop is bounded and cannot run indefinitely. |
| Lease unavailable | `blocked` | No action callback is invoked without ownership. |
| Loop guard rejection | `loop` | Repeated action fingerprint stops the cycle before action. |
| Context pack failure | `context_over` | The cycle stops instead of exceeding its budget. |
| Judge failure | `judge_fail` | Failed output is not promoted as successful work. |
| Action exception | `act_error` | The exception is bounded to a result and the lease is released. |
| Judge exception | `judge_error` | The exception is bounded to a result and the lease is released. |
| Memory write exception | `memory_error` | Failed writeback is bounded to a result and the lease is released. |
| Budget exception | `budget_error` | Budget failures are bounded to a result and the lease is released. |
| Budget exhaustion | `budget` | Further turns are denied after the bounded budget is consumed. |

The loop may write memory only after an action result is returned; promotion remains governed by the separate human-approval and evidence contracts. This is a local control-plane loop, not proof of autonomous external Hermes execution or self-learning without approval.

Every post-acquisition early stop releases the lease, including context-pack failure, loop-guard rejection, action exception, judge exception, memory write exception, and budget exception.
 Turn timestamps use an injectable clock so evidence tests can remain deterministic. The current conformance tests cover bounded turns, lease-miss action suppression, loop-guard stop, cleanup on failures, exception containment, deterministic timestamps, and judge-gated completion. External provider lanes remain disabled unless an operator supplies pinned environments and signed receipts.

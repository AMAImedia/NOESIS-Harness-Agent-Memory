# NOESIS Agent OS — evaluation protocol

Дата: 2026-08-17. Этот документ определяет, что означает «лучше» для NOESIS. Нельзя объявлять улучшение по количеству таблиц, файлов, токенов или агентов. Улучшение принимается только при росте измеримого результата без роста leakage, policy violations или irrecoverable failures.

## Benchmark dimensions

| Dimension | Primary metric | Required evidence |
|---|---|---|
| Long-term memory | answer F1/accuracy, temporal and multi-hop recall, adversarial abstention, source attribution | LoCoMo-style long conversations and a fixed local regression set |
| Context efficiency | useful evidence per injected token, retrieval precision@k, compaction retention, overflow rate | same tasks with fixed token budgets and full source IDs |
| Multi-agent coordination | task success, duplicate work, private-memory leakage, deadlock/starvation rate, critical-path latency | deterministic DAG scenarios with isolated scopes |
| Tool and policy reliability | final state correctness, policy violation rate, pass^k, approval fidelity | τ-bench-style stateful tool scenarios and side-effect ledger |
| Durable execution | recovery success after injected failures, exactly-once command rate, lost-checkpoint rate | fault injection at every checkpoint and restart boundary |
| Code productivity | tests passed, patch correctness, regression rate, human-review burden | a small pinned software-task set first; later SWE-bench-compatible adapter |
| Safety | prompt-injection detection, secret non-leakage, path/network deny rate, false-positive rate | adversarial corpus with deterministic expected outcomes |

## External references

LoCoMo evaluates long-term conversation using question answering, event-graph summarization and multimodal dialog over conversations of about 300 turns and up to 35 sessions, with single-hop, multi-hop, temporal and adversarial question types [1]. NOESIS should first implement an adapter that preserves source IDs and evaluates retrieval/answer evidence separately from model generation.

τ-bench evaluates dynamic tool-agent-user interaction under domain policies and compares the terminal database state with a goal state. It also reports pass^k reliability over repeated trials [2]. NOESIS should use the same idea for Gatekeeper approval and side-effect simulation: a run is successful only when the final state and policy trace both match the expected contract.

SWE-bench Verified is a human-validated 500-instance subset for coding agents [3]. NOESIS should not claim SWE-bench parity until it has a reproducible adapter with pinned environment, model, temperature, tool budget and patch verification. The first local gate is a smaller fixed task set that runs on the laptop.

## Baseline rules

Every experiment records repository revision or local file digest, Python/runtime version, model/provider identifier, temperature, token budget, tool capabilities, memory mode, number of agents, seed when supported, start/end time and all policy decisions. A result without these fields is non-comparable. All benchmark data and traces remain local.

The first comparison is A/B on the same task set: legacy 0.5 core versus the new nextgen layers. The model, prompt, task order and budget stay fixed. Metrics are reported with raw counts and denominators, not only percentages. A 95% confidence interval is required for repeated stochastic trials; deterministic unit tests are reported as pass/fail.

## Stop conditions

A change is rejected if it increases private-memory leakage, unauthorized side effects, unrecoverable task loss, or context-budget overflow, even when task success rises. A change is also rejected if its only gain comes from injecting more unverified text into the prompt. New memory must improve source-attributed recall or reduce repeated work on a held-out task.

## References

[1]: https://snap-research.github.io/locomo/ "LoCoMo long-term conversational memory benchmark"
[2]: https://arxiv.org/abs/2406.12045 "τ-bench tool-agent-user interaction benchmark"
[3]: https://www.swebench.com/verified.html "SWE-bench Verified"


## Phase 2 fault-injection gate — provider boundary

Provider interruption is evaluated as a lifecycle event, not as a successful empty response. An injected timeout must produce the deterministic `provider_timeout` error, while a truncated or malformed response body must produce `provider_invalid_json` or the relevant bounded-response error. Neither path may emit a committed invocation result or bypass the queue/recovery layer. The focused regression is `tests.test_provider_invocation`; the full suite must remain green and must not introduce `ResourceWarning`.


## Phase 2 fault-injection gate — durable checkpoint corruption

A malformed durable checkpoint is not treated as an empty state and is never passed to a runner. `FiberStore` raises `FiberCorrupt`, quarantines the record with `status='corrupted'` and `error='checkpoint_corrupt'`, and excludes it from `recoverable()`. Recovery may continue for other fibers, but the corrupted fiber requires an explicit operator repair or restore path.


## Phase 2 fault-injection gate — session resume and rollback boundary

A session interrupted during append may lose only the malformed final JSONL record. On reopen, `EventStore` repairs that tail, rebuilds the task projection, and preserves the last committed rollback state. A malformed record before a later valid record is treated as `EventStoreCorrupt` and stops replay rather than silently skipping history. A rollback transition remains resumable only through its explicit state-machine edge and a new command identifier; idempotency must not suppress a legitimate retry.

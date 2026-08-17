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

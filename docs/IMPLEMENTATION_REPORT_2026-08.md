# NOESIS-Harness-Agent-Memory — локальный implementation report

Дата: 2026-08-17. Изменения выполнены только в локальной папке ноутбука `NOESIS-Harness-Agent-Memory`. GitHub не публиковался и push не выполнялся.

## Что добавлено

В пакет добавлены `noesis_harness/nextgen.py`, `noesis_harness/governance.py`, `noesis_harness/fibers.py`, `noesis_harness/evidence.py`, `noesis_harness/security.py`, `noesis_harness/orchestration.py` и `noesis_harness/context_engine.py`. Последние два слоя добавляют dependency-aware WorkCoordinator с single-live-owner leases, reclaim и duplicate completion suppression, а также hard-budget context assembler с priority ordering, dropped-item audit и source provenance. Первая часть реализует `RunEnvelope`, deny-by-default `CapabilityManifest`, tamper-evident `AuditChain`, idempotent `DurableCommandLedger`, `AgentManifest`, `IsolationBroker`, `ResultEnvelope` и durable `ContextManager` с message tree, fork, non-destructive compaction и budgeted context packing.

Вторая часть реализует `Gatekeeper`, который различает deny/pending-simulation/approved; `DAGPlanner` с bounded parallelism и cycle rejection; атомарный `VaultProjector` для Obsidian-подобной Markdown projection; `SkillGate` с stage → test → approve/reject; и `ExecutionLadder`, которая честно возвращает `unavailable`, если hardened sandbox отсутствует. Добавлены `FiberStore` для checkpoint/resume после fault injection, `EvidenceStore` для provenance/freshness/conflict proposals и `SecurityScanner`/`LocalExecutionContract` для deterministic adversarial checks и explicit local execution planning.

Добавлены план `docs/PLAN_NOESIS_1.0_MASTER.md`, архитектура `docs/ARCHITECTURE_1.0_NEXTGEN.md`, evaluation protocol `docs/EVALUATION_PROTOCOL.md`, тесты новых слоёв и benchmarks `benchmarks/nextgen_bench.py` и `benchmarks/coordination_context_bench.py`. CHANGELOG и ROADMAP обновлены как local-only, not released.

## Проверка

| Проверка | Результат |
|---|---:|
| Существующий и новый unittest suite | **92/92 passed** |
| Новые nextgen tests | **6/6 passed** |
| Durable fiber tests | **2/2 passed** |
| Evidence memory tests | **3/3 passed** |
| Adversarial security tests | **3/3 passed** |
| Новые governance tests | **5/5 passed** |
| Public package exports smoke test | **1/1 passed** |
| Full regression duration | **2.541 s** |
| Hash-chain tamper detection | **passed** |
| Child → parent private-scope write denial | **passed** |
| Windows SQLite temporary-file cleanup | **passed** |
| Context compaction retains source IDs | **passed** |
| Missing hardened sandbox is reported as unavailable | **passed** |

## Benchmark, n=100

| Primitive | Measurement |
|---|---:|
| Audit append | 3,140.64 events/s |
| Context pack | 0.978 ms |
| DAG plan | 0.498 ms |
| Broker sends, 10 agents | 56.238 ms |
| 100 fiber register+checkpoint operations | 1,140.086 ms |
| 100 evidence adds + search | 555.982 ms |
| 100 safe-text security scans | 0.151 ms |
| 100 chained claims/completions | 1,413.490 ms |
| 100 context-engine assemblies | 0.120 ms |
| Context-engine dropped items at n=100 | 57 |
| Context-engine used tokens at n=100 | 989 / 1,000 budget |

These are local measurements, not universal performance claims. They are saved in the repository’s `_example_state/nextgen_benchmark.csv`.

## Honest boundary

This is a tested foundation slice, not yet a finished “best in the world” agent OS. The remaining high-risk work is a real hardened subprocess/Windows Sandbox adapter, larger public-data memory evaluation, repeated stochastic τ-bench-style state tests, and end-to-end real-model evaluations. The next verified roadmap is: add a public LoCoMo adapter; compare legacy versus evidence/context-engine A/B under identical budgets; add larger leakage and policy corpus; then evaluate a pinned coding-task adapter before any release decision. The current local slice has durable fibers/checkpoints, evidence-weighted conflict proposals and deterministic prompt-injection/secret/path tests, but does not claim that these replace an OS-level sandbox. The current code deliberately does not execute model-generated Python, does not claim in-process isolation, and does not auto-apply generated skills or external side effects.

The design borrows interfaces and principles rather than copying Cloudflare OS source: capability-based Gatekeepers, explicit sub-agent isolation, durable sessions, context compaction and an execution ladder are described by Cloudflare [1] [2]. Hermes’s bounded curated memory, staged writes, duplicate prevention and session search informed the memory/skill governance direction [3]. Pi’s minimal harness and explicit warning that it has no built-in permission system reinforced the decision to keep security in NOESIS rather than assume it from the model loop [4]. Letta’s distinction between in-context blocks, recall history, archival knowledge and sleep-time consolidation informed the memory tier separation [5].

## References

[1]: https://github.com/cloudflare/cloudflare-os "Cloudflare OS repository"
[2]: https://blog.cloudflare.com/project-think/ "Project Think: durable execution, sub-agents, sessions and sandboxed execution"
[3]: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory "Hermes Agent persistent memory"
[4]: https://github.com/badlogic/pi-mono "Pi Agent Harness repository"
[5]: https://www.letta.com/blog/agent-memory/ "Letta Agent Memory engineering overview"

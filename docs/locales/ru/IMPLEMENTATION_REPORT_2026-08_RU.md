# NOESIS-Harness-Agent-Memory — локальный implementation report

Дата: 2026-08-17. Изменения выполнены только в локальной папке ноутбука `NOESIS-Harness-Agent-Memory`. GitHub не публиковался и push не выполнялся.

## Что добавлено

В пакет добавлены `noesis_harness/nextgen.py`, `noesis_harness/governance.py`, `noesis_harness/fibers.py`, `noesis_harness/evidence.py`, `noesis_harness/security.py`, `noesis_harness/orchestration.py` и `noesis_harness/context_engine.py`. Последние два слоя добавляют dependency-aware WorkCoordinator с single-live-owner leases, reclaim и duplicate completion suppression, а также hard-budget context assembler с priority ordering, dropped-item audit и source provenance. Первая часть реализует `RunEnvelope`, deny-by-default `CapabilityManifest`, tamper-evident `AuditChain`, idempotent `DurableCommandLedger`, `AgentManifest`, `IsolationBroker`, `ResultEnvelope` и durable `ContextManager` с message tree, fork, non-destructive compaction и budgeted context packing.

Вторая часть реализует `Gatekeeper`, который различает deny/pending-simulation/approved; `DAGPlanner` с bounded parallelism и cycle rejection; атомарный `VaultProjector` для Obsidian-подобной Markdown projection; `SkillGate` с stage → test → approve/reject; и `ExecutionLadder`, которая честно возвращает `unavailable`, если hardened sandbox отсутствует. Добавлены `FiberStore` для checkpoint/resume после fault injection, `EvidenceStore` для provenance/freshness/conflict proposals и `SecurityScanner`/`LocalExecutionContract` для deterministic adversarial checks и explicit local execution planning.

Добавлены план `docs/locales/ru/PLAN_NOESIS_1.0_MASTER_RU.md`, архитектура `docs/ARCHITECTURE_1.0_NEXTGEN.md`, evaluation protocol `docs/locales/ru/EVALUATION_PROTOCOL_RU.md`, тесты новых слоёв и benchmarks `benchmarks/nextgen_bench.py` и `benchmarks/coordination_context_bench.py`. CHANGELOG и ROADMAP обновлены как local-only, not released.

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

## Best-state protection and rollback — 2026-08-17

Added `noesis_harness/best_state.py` with SQLite-durable verified-state history, monotonic best-score tracking, verifier rejection, explicit rollback, automatic recovery, rollback audit events and fail-soft unavailable status for missing runs. The layer records candidate payload digests but never executes artifacts or claims OS-level isolation.

| Check | Result |
|---|---:|
| Focused best-state tests | **6/6 passed** |
| Full regression after addition | **98/98 passed in 2.692 s** |
| Candidate recording benchmark, n=100 | **793.404 ms** |
| Regessions kept out of best-state | **20** |
| Late regression before recovery | **0.05** |
| Best score after recovery | **0.98** |
| Rollback events | **1** |
| Recovery status | **recovered** |
| Recovery latency | **7.320 ms** |

The benchmark intentionally ends with a verified late regression. `recover()` restores the best accepted state, records one rollback event, and becomes a no-op when invoked again. This is a local measurement, not a universal performance claim.

## Fiber/lease recovery integration — 2026-08-17

Added `FiberStore.restore` and `RecoveryCoordinator`, joining `BestStateStore`, `FiberStore` and `WorkCoordinator`. Recovery restores only the verified best state, records an explicit fiber restore event, reclaims expired leases, and leaves live leases untouched. Missing best state or fiber is reported fail-soft rather than treated as success.

| Check | Result |
|---|---:|
| Recovery integration tests | **2/2 passed** |
| Full regression after integration | **100/100 passed in 2.866 s** |
| Crash cycles benchmark | **100/100 recovered** |
| Expired leases reclaimed | **100/100** |
| Recovery benchmark total | **11185.187 ms** |
| Average cycle | **111.852 ms** |

The benchmark uses deterministic local SQLite state and fault-shaped late regressions. It measures the recovery control plane only; it does not claim process isolation, hardened sandboxing or universal agent quality.

## Controlled memory A/B, trajectory evaluation and security holdouts — 2026-08-17

Added `ControlledMemoryEvaluator` for a same-budget legacy stable-prefix baseline versus provenance-aware next-generation assembly. The evaluator reports source recall, transfer gain, selected/dropped IDs and hard-cap compliance. Added deterministic `TrajectoryEvaluator` with C1 Solution Framing, C2 Execution and C3 Feedback Control proxies from recorded checkpoints; it reports peak retention, dips, recovery credit, delivery rate and build-error rate. Core metrics do not use an LLM judge.

| Check | Result |
|---|---:|
| Controlled memory A/B tests | **3/3 passed** |
| Memory A/B n=100 legacy source recall | **0.000000** |
| Memory A/B n=100 nextgen source recall | **1.000000** |
| Memory A/B n=100 transfer gain | **+1.000000** |
| Memory A/B hard-cap rate | **1.000000** |
| Memory assembly time, n=100 | **1.382 ms** |
| Trajectory avg@3 | **0.800000** |
| Trajectory best@3 | **0.900000** |
| Trajectory C1/C2/C3 | **0.511111 / 1.000000 / 1.000000** |
| Security holdout cases | **12** |
| Security holdout pass rate, n=100 | **1.000000** |
| Security holdout mean scan time | **0.381847 ms** |
| Full regression after all additions | **112/112 passed in 2.947 s** |

The A/B fixture is deliberately fixed and diagnostic, not a claim of universal memory superiority. Negative transfer remains observable and is tested explicitly. The security corpus tests deny/allow behavior, while hardened OS-level isolation remains unavailable unless an external sandbox is explicitly provided.

## P0 UI Contract and health endpoint — 2026-08-17

Implemented `noesis_harness/ui_contract.py` and `noesis_harness/health_server.py` as stdlib-only control-plane foundations. UI Contract v1 defines deterministic envelopes, request IDs, health/model metadata, adapter failure statuses and recursive secret redaction. The read-only `HealthServer` defaults to `127.0.0.1`, supports a random loopback port, reports `ready` versus `degraded` when optional Hermes/DeepSeek/sandbox capabilities are unavailable, rejects non-loopback construction, denies POST requests, returns structured unknown-path errors and shuts down cleanly.

| Check | Result |
|---|---:|
| Focused P0 contract/health tests | **6/6 passed in 1.553 s** |
| Full regression after P0 code | **124/124 passed in 4.623 s** |
| Health benchmark requests | **100** |
| Health benchmark error rate | **0.000000** |
| Health p50 / p95 | **0.744900 / 22.139500 ms** |
| Health mean latency | **4.868805 ms** |
| Mean response size | **517 bytes** |
| Default Hermes adapter status | **unavailable** until optional bridge is configured |
| Default DeepSeek adapter status | **unavailable** until optional bridge is configured |
| Hardened sandbox status | **unavailable** unless an external hardened provider is present |

The portable UI roadmap now explicitly includes the Windows/macOS DeepSeek Harness + Hermes WebUI adapter layer as P5-00. These runtimes remain optional child processes; the NOESIS core does not depend on Node, does not merge their private memory implicitly and does not expose provider credentials to the browser.

## P0-03 Provider registry and `/models` endpoint — 2026-08-17

Added `noesis_harness/provider_registry.py` and extended `HealthServer` with a read-only `GET /models` route. The registry is declarative and in-memory: it stores only provider/model IDs, endpoint kind, status and capability metadata. It never stores credentials, calls an upstream provider or treats a missing runtime as ready. The fixture set covers Ollama, LM Studio, llama.cpp, vLLM and OpenAI-compatible providers. Hermes WebUI and DeepSeek Harness remain explicit optional adapter kinds and default to `unavailable` until configured.

| Check | Result |
|---|---:|
| Provider registry focused tests | **6/6 passed in 1.022 s** |
| Full regression after P0-03 | **130/130 passed in 5.043 s** |
| Provider fixture kinds | **5** |
| `/models` benchmark requests | **100** |
| `/models` error rate | **0.000000** |
| Registry serialization p50 / p95 | **0.184600 / 0.218100 ms** |
| `/models` HTTP p50 / p95 | **1.093300 / 20.626600 ms** |
| `/models` HTTP mean | **7.293836 ms** |
| Empty registry behavior | **explicit `unavailable`, empty models; never fake ready** |
| Metadata secret scan | **clean** |

A first benchmark fixture omission was detected because default provider status is intentionally `unavailable`; the fixture was corrected to explicitly set `status="ready"` for verified local test providers. This is preserved as a regression lesson: adapter readiness must always be declared, never inferred from descriptor presence. During the pre-commit scan, a historical credential-like security-test fixture was also replaced with a synthetic value that still exercises the `api_token` rule. The current high-confidence secret scan is clean; historical Git history was not rewritten automatically.

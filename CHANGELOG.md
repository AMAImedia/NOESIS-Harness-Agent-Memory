# Changelog

All notable changes to NOESIS-Harness-Agent-Memory are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Trust Plane provenance, lineage, Gatekeeper and child-runtime security closeout evidence.
- Versioned task/session command API, bounded SSE stream contract and approval-gated TaskExecutionBridge.
- SafeParallelExecutor with per-agent workspaces, durable Actions lifecycle and RecoveryCoordinator requeue.
- Portable artifact manifest/SBOM verifier and native Windows/macOS dry-run/signing-policy evidence lanes.
- Operator-owned migration mode source with HMAC-signed receipts persisted transactionally in the SQLite/WAL administrative audit store.
- Read-only `/api/audit/migration` endpoint and SSE/UI audit timeline rendering for the latest signed migration receipts.

### Changed
- Python 3.14 is the sole target runtime; CI packaging gates now verify portable SHA-256/SPDX coverage and both native target mismatch paths.

### Security
- Offline release audit is network-off-by-default and checks credential-like strings, AST eval/exec calls, package exports and clean Git state.

### Verification snapshot — 2026-08-18
- Gate 3 child-runtime progress: `ExecutionRequest` binds `SkillManifest` identity to explicit capability grants; strict executable-skill mode requires a hardened backend; Linux/Bubblewrap adversarial probes verify host filesystem and outbound network isolation; HMAC receipt persistence, durable patch review, interrupted-run recovery and authenticated operator rollback binding are locally verified. Native Windows/macOS evidence remains open.
- Gate 4 progress: `MultiAgentWorkProductLoop` binds exclusive claims to typed work-product envelopes, per-agent snapshots, independent review, fresh-base authorization, explicit commit markers and durable resume/replay. MA-06 adds bounded retry/reclaim, cancellation non-retry, a 12-case cross-agent leakage corpus and deterministic quality metrics. MA-07 adds a three-lane parallel workload runner with injected crash/retry, SQLite/WAL result aggregation, completed-run replay and conflict rejection. MA-08 verifies crash injection before/after write/read and repeated mean/p50/p95 distributions. MA-09 verifies four simultaneous active-delegation sibling/path leakage probes; broader protocol/provider leakage remains open.
- Gate 5 progress: `MemoryQualityEvaluator` reports separate recall, attribution precision, conflict, temporal, compaction-retention, hard-budget, leakage-free and experience-reuse recall evidence from verifier/source IDs without model self-grading. `DurableMemoryQualityAdapter` now persists/reopens query-aware traces beside `Memory`; MEM-09 runs a real stdlib `Memory` + `ExperienceReuseSelector` trajectory over four persisted semantic facts with recall 0.75, attribution precision 1.0, reuse recall 1.0, budget compliance 1.0 and four reopened traces. Adversarial tests cover query/trace conflict, attribution leakage, budget violation, decay floor and restart persistence. The 64-token fixture distribution at scales 32/128/512/1024 over five repetitions remains baseline recall 0.0, nextgen recall 1.0, gain 1.0. Evidence schema is v2; this is deterministic local evidence, not an external model benchmark.
- Gate 6 preparation: fail-closed Windows PowerShell and macOS shell parity bundles now have a unified stdlib `validate_native_parity.py` CLI and `validate_native_artifacts` API. Matching-host validation rejects missing/malformed artifacts, guard violations, stale/non-passed parity results and SHA-256 manifest mismatches; ten native negative/contract cases pass locally. Matching-host execution remains `not_run`.
- Python 3.14.7 full regression: 469 tests passed with `ResourceWarning` treated as an error; link, documentation security, JSON evidence, metadata, and packaging consistency audits passed.
- Offline release audit remains claim-conservative: the synthetic private-key holdout fixture is intentional, while native target builds and external A/B remain unreleased gates; the pushed checkpoint tree is clean.
- Reconciled the normative English/Russian master roadmap, root roadmap navigation, self-learning maturity audit and operational checklist; bounded production lifecycle and durable promotion-state/evaluator deployment are locally verified, while governed executable child runtime is in progress with Linux-only isolation evidence.

## [0.5.0] - 2026-08-14

### Added
- MemoryGraph, ScopedMemory, Budget, HitlGate.
- ContextVfs (L0/L1/L2), extract_session, McpServer.
- benchmarks/recall20 (20/20).
- ALTER migrate for `memories.embedding` on old DBs.

### Changed
- README is self-contained for GitHub (no parent digest required).

## [0.4.0] - 2026-08-14

### Added
- Vector tier + configurable RRF fusion (optional backends; stdlib fallback).
- `PrivacyFilter`, snapshot export/import with LWW merge.
- `ConsolidationWorker`, `ProcedureRunner`.
- `Mesh` + HTTP snapshot peer; `InspectUI` (`noesis-inspect`).
- `AgentTrace` + `HybridJudge`.
- `DurableQueue` (WAL, dedup, retry, recover) and `LoopGuard`.
- Tests: 57+ stdlib unittest cases.

### Changed
- Package version 0.2.0 -> 0.4.0.

## [0.2.0] - 2026-08-14

### Added
- `docs/architecture.md`, `docs/api.md`, `docs/why.md` - full documentation suite.
- `examples/multi_agent_swarm.py` - 3 agents + coordination on a shared EventStore.
- `examples/memory_tiers.py` - 4-tier memory + decay + offload demo.
- `examples/dag_actions.py` - Actions DAG with typed edges + auto-unblock.
- `integrations/claude_code.py` - Claude Code bridge (local adapter, STUB).
- `integrations/codex.py` - OpenAI Codex CLI bridge (local adapter, STUB).
- `integrations/openclaw.py` - OpenClaw bridge + coordination (local adapter, STUB).
- `benchmarks/memory_bench.py` + `benchmarks/run_bench.py` - EventStore/Memory benchmarks.
- `.github/workflows/ci.yml` - CI on Python 3.9-3.12, examples, benchmarks, build, lint.
- `py.typed` marker for PEP 561.

### Changed
- `pyproject.toml` 0.1.0 -> 0.2.0; SPDX license expression; beta classifier.

## [0.1.0] - 2026-08-14

### Added
- `noesis_harness/event_store.py` - append-only JSONL + deterministic projection.
- `noesis_harness/memory.py` - 4-tier memory + FTS5 + decay + symbolic offload.
- `noesis_harness/coordination.py` - Leases (TTL), Signals (mailbox), Actions (DAG).
- `tests/test_core.py` - 15 stdlib tests (no deps).
- `examples/botfarm_lead.py` - worked example.
- README, AGENTS.md, LICENSE (MIT), pyproject.toml, .gitignore.

### Local development slice (not released)
- [x] Added stdlib-only `nextgen.py`: run envelopes, hash-chain audit, idempotent ledger, scoped agent broker, message-tree context and non-destructive compaction.
- [x] Added stdlib-only `governance.py`: capability Gatekeeper, DAG planner, Obsidian vault projection, staged skills and honest execution ladder.
- [x] Added 11 local tests and benchmark `benchmarks/nextgen_bench.py`; full suite passes locally.
- [ ] Remaining: durable fibers, richer memory conflict resolution, hardened subprocess/sandbox adapters and adversarial benchmark corpus.
